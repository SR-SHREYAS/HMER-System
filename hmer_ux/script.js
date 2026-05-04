let predictedSeq = "";
let translatedLatex = "";
const BASE_URL = window.location.origin;
const DRAW_BG = 'white';
const DRAW_FG = 'black';
const MODEL_BG = 'black';


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
    } else if (data.error) {
      document.getElementById('latexRender').innerHTML = `<span class="text-red-600">${data.error}</span>`;
      document.getElementById('seqResult').value = '';
      document.getElementById('latexSource').value = '';
    }
  })
  .catch(err => {
    console.error(err);
    document.getElementById('latexRender').innerHTML = '<span class="text-red-600">Error generating sequence</span>';
    document.getElementById('seqResult').value = '';
    document.getElementById('latexSource').value = '';
  });
}

function generateLatex(sequence) {
  const latexContainer = document.getElementById('latexRender');
  latexContainer.innerHTML = `$$${sequence}$$`; // MathJax format
  MathJax.typesetPromise([latexContainer]);
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

document.getElementById('sendCanvasBtn').addEventListener('click', () => {
  const processedCanvas = preprocessCanvasForModel(canvas);
  if (!processedCanvas) {
    document.getElementById('latexRender').innerHTML = '<span class="text-red-600">Please write something first</span>';
    document.getElementById('seqResult').value = '';
    document.getElementById('latexSource').value = '';
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
      } else if (data.error) {
        document.getElementById('latexRender').innerHTML = `<span class="text-red-600">${data.error}</span>`;
        document.getElementById('seqResult').value = '';
        document.getElementById('latexSource').value = '';
      }
    })
    .catch(err => {
      console.error(err);
      document.getElementById('latexRender').innerHTML = '<span class="text-red-600">Error generating LaTeX</span>';
      document.getElementById('seqResult').value = '';
      document.getElementById('latexSource').value = '';
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
