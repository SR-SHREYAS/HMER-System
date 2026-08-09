let predictedSeq = "";
let translatedLatex = "";
const BASE_URL = window.location.origin;
const SOLVE_URL = BASE_URL + '/solve';
const DRAW_BG = 'white';
const DRAW_FG = 'black';
const MODEL_BG = 'black';
let solving = false;


document.getElementById('imageInput').addEventListener('change', function(event) {
  const file = event.target.files[0];
  const preview = document.getElementById('previewImage');
  const errorDiv = document.getElementById('imageError');
  if (file) {
    const reader = new FileReader();
    reader.onload = function(e) {
      preview.src = e.target.result;
      preview.classList.remove('hidden');
      errorDiv.classList.add('hidden');
      predictSequence(file);
    };
    reader.onerror = function() {
      preview.classList.add('hidden');
      errorDiv.classList.remove('hidden');
    };
    reader.readAsDataURL(file);
  } else {
    preview.classList.add('hidden');
    errorDiv.classList.add('hidden');
  }
});

function predictSequence(imageFile) {
  const formData = new FormData();
  formData.append('image', imageFile);
  fetch(BASE_URL + '/predict', {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.sequence) {
      predictedSeq = data.sequence;
      translatedLatex = data.latex || data.sequence;
      document.getElementById('seqResult').value = predictedSeq;
      document.getElementById('latexSource').value = translatedLatex;
      generateLatex(translatedLatex);
      solveLatex(translatedLatex);
    } else if (data.error) {
      document.getElementById('latexRender').innerHTML = `<span class="text-red-600">${data.error}</span>`;
      document.getElementById('seqResult').value = '';
      document.getElementById('latexSource').value = '';
      resetPredictionDetails();
    }
  })
  .catch(err => {
    console.error(err);
    document.getElementById('latexRender').innerHTML = '<span class="text-red-600">Error generating sequence</span>';
    document.getElementById('seqResult').value = '';
    document.getElementById('latexSource').value = '';
    resetPredictionDetails();
  });
}

function generateLatex(sequence) {
  const latexContainer = document.getElementById('latexRender');
  latexContainer.innerHTML = `$$${sequence}$$`; // MathJax format
  MathJax.typesetPromise([latexContainer]);
}

// Build the task, answer and step DOM from the backend response, then let
// animation.js progressively reveal it.
function renderPredictionDetails(data) {
  const task = String(data.task || 'unknown');
  const isKnownTask = task.toLowerCase() !== 'unknown';

  const taskNode = document.getElementById('taskResult');
  const answerSection = document.getElementById('answerSection');
  const answerResult = document.getElementById('answerResult');
  const stepsSection = document.getElementById('stepsSection');
  const stepsContainer = document.getElementById('stepsResult');

  taskNode.textContent = task.charAt(0).toUpperCase() + task.slice(1);

  const hasAnswer = data.answer != null && String(data.answer).trim() !== '';
  answerResult.textContent = hasAnswer ? data.answer : '';

  const stepNodes = isKnownTask ? buildStepNodes(data.steps || [], stepsContainer) : [];

  playSolutionAnimation({
    taskNode: taskNode,
    answerSection: answerSection,
    stepsSection: stepsSection,
    stepNodes: stepNodes,
    showSteps: isKnownTask,
    showAnswer: isKnownTask && hasAnswer
  });
}

function buildStepNodes(steps, container) {
  container.innerHTML = '';
  if (!steps || steps.length === 0) {
    return [];
  }

  const nodes = [];
  steps.forEach((step, index) => {
    const item = document.createElement('li');
    item.className = 'border rounded p-3';

    const heading = document.createElement('div');
    heading.className = 'font-semibold';
    heading.textContent = `Step ${index + 1}: ${step.title || ''}`.trim();
    item.appendChild(heading);

    // Optional rule name from metadata (e.g. "trig_rule" -> "trig").
    const kind = step.rule || (step.metadata && step.metadata.kind);
    if (kind) {
      const rule = document.createElement('span');
      rule.className = 'inline-block text-xs px-2 py-0.5 bg-blue-100 text-blue-800 rounded mt-1';
      rule.textContent = String(kind).replace(/_/g, ' ');
      item.appendChild(rule);
    }

    if (step.description) {
      const desc = document.createElement('p');
      desc.className = 'text-gray-700 mt-1';
      desc.textContent = step.description;
      item.appendChild(desc);
    }

    const math = document.createElement('div');
    math.className = 'mt-1';
    math.innerHTML = `$$${step.latex || ''}$$`;
    item.appendChild(math);

    container.appendChild(item);
    nodes.push(item);
  });

  MathJax.typesetPromise([container]).catch(err => console.warn('MathJax step error', err));
  return nodes;
}

function resetPredictionDetails() {
  resetSolutionAnimation();
  document.getElementById('taskResult').textContent = '';
  document.getElementById('answerResult').textContent = '';
  document.getElementById('errorResult').textContent = '';
  document.getElementById('stepsResult').innerHTML = '';
  document.getElementById('solveStatus').classList.add('section-hidden');
  document.getElementById('errorSection').classList.add('section-hidden');
  restoreSendButton();
}

// ---------------------------------------------------------------------------
// /solve integration: after OCR produces LaTeX, POST it to the API and show
// the final result plus the step-by-step solution.
// ---------------------------------------------------------------------------

function solveLatex(latex) {
  if (!latex || solving) return;
  solving = true;

  const sendBtn = document.getElementById('sendCanvasBtn');
  const status = document.getElementById('solveStatus');
  const errorSection = document.getElementById('errorSection');
  const answerSection = document.getElementById('answerSection');
  const stepsSection = document.getElementById('stepsSection');
  const taskNode = document.getElementById('taskResult');

  // Cancel any pending reveal, show the loading state and block repeats.
  cancelSolutionAnimation();
  sendBtn.disabled = true;
  sendBtn.textContent = 'Solving…';
  status.classList.remove('section-hidden');
  answerSection.classList.add('section-hidden');
  stepsSection.classList.add('section-hidden');
  errorSection.classList.add('section-hidden');
  document.getElementById('answerResult').textContent = '';
  document.getElementById('errorResult').textContent = '';
  document.getElementById('stepsResult').innerHTML = '';

  fetch(SOLVE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ input: latex, type: 'derivative' })
  })
  .then(res => res.json())
  .then(data => {
    solving = false;
    status.classList.add('section-hidden');
    restoreSendButton();
    taskNode.textContent = 'Derivative';
    if (data.success) {
      renderSolveSuccess(data);
    } else {
      renderSolveError(data.error || 'Failed to solve expression');
    }
  })
  .catch(err => {
    console.error(err);
    solving = false;
    status.classList.add('section-hidden');
    restoreSendButton();
    taskNode.textContent = 'Derivative';
    renderSolveError('Network error while solving: ' + err.message);
  });
}

function restoreSendButton() {
  const sendBtn = document.getElementById('sendCanvasBtn');
  sendBtn.disabled = false;
  sendBtn.textContent = 'Send';
}

function renderSolveSuccess(data) {
  const taskNode = document.getElementById('taskResult');
  const answerSection = document.getElementById('answerSection');
  const answerResult = document.getElementById('answerResult');
  const stepsSection = document.getElementById('stepsSection');
  const stepsContainer = document.getElementById('stepsResult');

  const resultLatex = (data.result || '').trim();

  // Render the final result through MathJax.
  answerResult.innerHTML = '';
  if (resultLatex) {
    const math = document.createElement('div');
    math.className = 'text-base';
    math.innerHTML = `$$${resultLatex}$$`;
    answerResult.appendChild(math);
  } else {
    answerResult.textContent = '(no result)';
  }

  const stepNodes = buildStepNodes(data.steps || [], stepsContainer);
  const hasResult = resultLatex !== '';

  // Reveal task, steps and answer progressively.
  requestAnimationFrame(() => {
    playSolutionAnimation({
      taskNode: taskNode,
      answerSection: answerSection,
      stepsSection: stepsSection,
      stepNodes: stepNodes,
      showSteps: stepNodes.length > 0,
      showAnswer: hasResult
    });
  });

  // Ensure the rendered result math typesets after reveal.
  if (resultLatex) {
    MathJax.typesetPromise([answerResult]).catch(err => console.warn('MathJax result error', err));
  }
}

function renderSolveError(message) {
  const errorSection = document.getElementById('errorSection');
  const errorResult = document.getElementById('errorResult');
  const answerSection = document.getElementById('answerSection');
  const stepsSection = document.getElementById('stepsSection');

  errorResult.textContent = message;
  resetSolutionAnimation();
  errorSection.classList.remove('section-hidden');
  answerSection.classList.add('section-hidden');
  stepsSection.classList.add('section-hidden');
}

// Tab switching logic
function showTab(tab) {
  const uploadSection = document.getElementById('upload-section');
  const drawSection = document.getElementById('draw-section');
  const tabUpload = document.getElementById('tab-upload');
  const tabDraw = document.getElementById('tab-draw');
  if (tab === 'upload') {
    uploadSection.classList.remove('hidden');
    drawSection.classList.add('hidden');
    tabUpload.classList.add('border-l', 'border-t', 'border-r', 'rounded-t', 'font-semibold', 'text-blue-700');
    tabDraw.classList.remove('border-l', 'border-t', 'border-r', 'rounded-t', 'font-semibold', 'text-blue-700');
  } else {
    uploadSection.classList.add('hidden');
    drawSection.classList.remove('hidden');
    tabDraw.classList.add('border-l', 'border-t', 'border-r', 'rounded-t', 'font-semibold', 'text-blue-700');
    tabUpload.classList.remove('border-l', 'border-t', 'border-r', 'rounded-t', 'font-semibold', 'text-blue-700');
  }
}

// Canvas drawing logic
const canvas = document.getElementById('drawCanvas');
const ctx = canvas.getContext('2d');
let drawing = false;

// Keep the drawing surface comfortable for the user.
ctx.fillStyle = DRAW_BG;
ctx.fillRect(0, 0, canvas.width, canvas.height);
ctx.strokeStyle = DRAW_FG;
ctx.lineWidth = 5;
ctx.lineCap = 'round';
ctx.lineJoin = 'round';

canvas.addEventListener('mousedown', (e) => {
  drawing = true;
  ctx.beginPath();
  ctx.moveTo(e.offsetX, e.offsetY);
});
canvas.addEventListener('mousemove', (e) => {
  if (drawing) {
    ctx.lineTo(e.offsetX, e.offsetY);
    ctx.stroke();
  }
});
canvas.addEventListener('mouseup', () => {
  drawing = false;
});
canvas.addEventListener('mouseleave', () => {
  drawing = false;
});

document.getElementById('clearCanvasBtn').addEventListener('click', () => {
  ctx.fillStyle = DRAW_BG;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
});

showTab('draw');

document.getElementById('sendCanvasBtn').addEventListener('click', () => {
  const processedCanvas = preprocessCanvasForModel(canvas);
  if (!processedCanvas) {
    document.getElementById('latexRender').innerHTML = '<span class="text-red-600">Please write something first</span>';
    document.getElementById('seqResult').value = '';
    document.getElementById('latexSource').value = '';
    resetPredictionDetails();
    return;
  }

  processedCanvas.toBlob(function(blob) {
    const formData = new FormData();
    formData.append('image', blob, 'drawn-processed.png');
    fetch(BASE_URL + '/predict', {
      method: 'POST',
      body: formData
    })
    .then(res => res.json())
    .then(data => {
      if (data.sequence) {
        predictedSeq = data.sequence;
        translatedLatex = data.latex || data.sequence;
        document.getElementById('seqResult').value = predictedSeq;
        document.getElementById('latexSource').value = translatedLatex;
        generateLatex(translatedLatex);
        solveLatex(translatedLatex);
      } else if (data.error) {
        document.getElementById('latexRender').innerHTML = `<span class="text-red-600">${data.error}</span>`;
        document.getElementById('seqResult').value = '';
        document.getElementById('latexSource').value = '';
        resetPredictionDetails();
      }
    })
    .catch(err => {
      console.error(err);
      document.getElementById('latexRender').innerHTML = '<span class="text-red-600">Error generating LaTeX</span>';
      document.getElementById('seqResult').value = '';
      document.getElementById('latexSource').value = '';
      resetPredictionDetails();
    });
  }, 'image/png');
});


function preprocessCanvasForModel(sourceCanvas) {
  const sourceCtx = sourceCanvas.getContext('2d');
  const { width, height } = sourceCanvas;
  const imageData = sourceCtx.getImageData(0, 0, width, height);
  const bounds = findInkBounds(imageData, width, height);

  if (!bounds) {
    return null;
  }

  const cropWidth = bounds.maxX - bounds.minX + 1;
  const cropHeight = bounds.maxY - bounds.minY + 1;
  const padding = Math.max(12, Math.round(Math.max(cropWidth, cropHeight) * 0.2));

  const cropped = document.createElement('canvas');
  cropped.width = cropWidth;
  cropped.height = cropHeight;
  const croppedCtx = cropped.getContext('2d');
  const croppedImage = sourceCtx.getImageData(bounds.minX, bounds.minY, cropWidth, cropHeight);
  invertToModelStyle(croppedImage.data);
  croppedCtx.putImageData(croppedImage, 0, 0);

  const output = document.createElement('canvas');
  output.width = cropWidth + padding * 2;
  output.height = cropHeight + padding * 2;
  const outputCtx = output.getContext('2d');
  outputCtx.fillStyle = MODEL_BG;
  outputCtx.fillRect(0, 0, output.width, output.height);
  outputCtx.imageSmoothingEnabled = true;
  outputCtx.drawImage(cropped, padding, padding);

  return output;
}


function findInkBounds(imageData, width, height) {
  const data = imageData.data;
  let minX = width;
  let minY = height;
  let maxX = -1;
  let maxY = -1;

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4;
      const value = data[idx];
      if (value < 245) {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    }
  }

  if (maxX === -1) {
    return null;
  }

  return { minX, minY, maxX, maxY };
}


function invertToModelStyle(data) {
  for (let i = 0; i < data.length; i += 4) {
    const gray = data[i];
    const inverted = 255 - gray;
    data[i] = inverted;
    data[i + 1] = inverted;
    data[i + 2] = inverted;
    data[i + 3] = 255;
  }
}
