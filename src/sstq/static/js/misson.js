document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("tipModal");
  const modalContent = document.getElementById("tipModalContent");
  const modalModeLabel = document.getElementById("tipModalModeLabel");
  const modalTimer = document.getElementById("tipModalTimer");
  const triggers = Array.from(document.querySelectorAll("[data-tip-trigger]"));
  const closeControls = Array.from(document.querySelectorAll("[data-tip-close]"));

  if (!modal || !modalContent || !modalModeLabel || !modalTimer || triggers.length === 0) {
    return;
  }

  let timerId = null;
  let countdownId = null;
  let activeTrigger = null;

  const stopTimers = () => {
    window.clearTimeout(timerId);
    window.clearInterval(countdownId);
    timerId = null;
    countdownId = null;
  };

  const closeModal = () => {
    stopTimers();
    modal.hidden = true;
    modalContent.innerHTML = "";
    modalTimer.hidden = true;
    modalTimer.textContent = "";

    if (activeTrigger?.dataset.tipMode === "normal") {
      activeTrigger.dataset.tipUsed = "true";
      activeTrigger.disabled = true;
      activeTrigger.textContent = "Tips Used";
    }
    activeTrigger = null;
  };

  const startNormalTimer = (seconds) => {
    let remaining = seconds;
    modalTimer.hidden = false;
    modalTimer.textContent = `Tips close in ${remaining}s`;

    countdownId = window.setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) {
        closeModal();
        return;
      }
      modalTimer.textContent = `Tips close in ${remaining}s`;
    }, 1000);

    timerId = window.setTimeout(() => {
      closeModal();
    }, seconds * 1000);
  };

  triggers.forEach((trigger) => {
    trigger.addEventListener("click", () => {
      const template = trigger.parentElement?.nextElementSibling;
      const mode = trigger.dataset.tipMode || "easy";
      const seconds = Number.parseInt(trigger.dataset.tipSeconds || "0", 10);
      const alreadyUsed = trigger.dataset.tipUsed === "true";
      if (!(template instanceof HTMLTemplateElement)) {
        return;
      }
      if (mode === "normal" && alreadyUsed) {
        return;
      }

      stopTimers();
      activeTrigger = trigger;
      modalContent.innerHTML = template.innerHTML;
      modal.hidden = false;
      modalModeLabel.textContent = mode === "normal" ? "Timed Tips" : "Tips";

      if (mode === "normal" && seconds > 0) {
        startNormalTimer(seconds);
      } else {
        modalTimer.hidden = true;
        modalTimer.textContent = "";
      }
    });
  });

  closeControls.forEach((control) => {
    control.addEventListener("click", closeModal);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) {
      closeModal();
    }
  });
});
