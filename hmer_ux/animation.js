/* animation.js
 *
 * Controls the progressive, timed reveal of the solution details that were
 * already rendered by script.js. This module only decides when the existing
 * DOM becomes visible; it makes no network requests and holds no logic about
 * the Math engine.
 *
 * Timeline:
 *   - Rendered LaTeX is shown by script.js immediately.
 *   - Recognized Task appears after TASK_DELAY_MS.
 *   - Steps appear one by one, STEP_GAP_MS apart.
 *   - Final Answer appears right after the last step (or immediately when
 *     there are no steps).
 */
(function () {
  'use strict';

  var TASK_DELAY_MS = 300;
  var FIRST_STEP_DELAY_MS = 300;
  var STEP_GAP_MS = 700;

  var currentToken = 0;

  function isCurrent(token) {
    return token === currentToken;
  }

  function delay(ms) {
    return new Promise(function (resolve) {
      setTimeout(resolve, ms);
    });
  }

  // Put an element into its initial hidden state, ready to be revealed.
  function prepareReveal(node) {
    if (!node) return;
    node.classList.remove('section-hidden');
    node.classList.remove('solution-visible');
    node.classList.add('solution-reveal');
  }

  // Completely hide a section that must not appear at all.
  function hideSection(node) {
    if (!node) return;
    node.classList.add('section-hidden');
    node.classList.remove('solution-reveal', 'solution-visible');
  }

  // Show a section header without fading it (keeps label + list container).
  function showSection(node) {
    if (!node) return;
    node.classList.remove('section-hidden', 'solution-reveal', 'solution-visible');
  }

  // Fade an element in from its prepared (hidden) state.
  function reveal(node) {
    if (!node) return;
    node.classList.remove('section-hidden');
    node.classList.add('solution-reveal');
    void node.offsetWidth; // force style flush so the transition triggers
    node.classList.add('solution-visible');
  }

  // Starts the timed reveal. Overwrites any animation currently running.
  function playSolutionAnimation(options) {
    var token = ++currentToken;
    var taskNode = options.taskNode;
    var answerSection = options.answerSection;
    var stepsSection = options.stepsSection;
    var stepNodes = options.stepNodes || [];
    var showSteps = options.showSteps;
    var showAnswer = options.showAnswer;

    // Prepare initial states up-front so nothing flashes before the reveal.
    prepareReveal(taskNode);
    if (showSteps) {
      showSection(stepsSection);
      stepNodes.forEach(prepareReveal);
    } else {
      hideSection(stepsSection);
    }
    if (showAnswer) {
      prepareReveal(answerSection);
    } else {
      hideSection(answerSection);
    }

    (async function run() {
      // No steps: show the final answer immediately.
      if (!showSteps && showAnswer) {
        reveal(answerSection);
      }

      await delay(TASK_DELAY_MS);
      if (!isCurrent(token)) return;
      reveal(taskNode);

      if (showSteps) {
        await delay(FIRST_STEP_DELAY_MS);
        if (!isCurrent(token)) return;
        showSection(stepsSection);
        if (stepNodes.length) reveal(stepNodes[0]);

        for (var i = 1; i < stepNodes.length; i++) {
          await delay(STEP_GAP_MS);
          if (!isCurrent(token)) return;
          reveal(stepNodes[i]);
        }

        if (showAnswer) {
          reveal(answerSection);
        }
      }
    })();
  }

  // Stop any running reveal animation (does not touch the DOM).
  function cancelSolutionAnimation() {
    currentToken++;
  }

  // Stop any running animation and reset the solution DOM to its idle state.
  function resetSolutionAnimation() {
    currentToken++;
    [
      document.getElementById('taskResult'),
      document.getElementById('answerSection'),
      document.getElementById('stepsSection')
    ].forEach(hideSection);
  }

  window.playSolutionAnimation = playSolutionAnimation;
  window.cancelSolutionAnimation = cancelSolutionAnimation;
  window.resetSolutionAnimation = resetSolutionAnimation;
})();
