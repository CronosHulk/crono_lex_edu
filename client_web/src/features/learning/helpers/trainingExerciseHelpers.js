export function readFeedbackOptionLabels(data, fallbackOptions) {
  if (Array.isArray(data?.feedback_options) && data.feedback_options.length === fallbackOptions.length) {
    return data.feedback_options;
  }
  const buttons = Array.isArray(data?.screen?.buttons) ? data.screen.buttons : [];
  const labels = buttons
    .filter((button) => button?.action === "noop")
    .map((button) => button?.text)
    .filter((text) => typeof text === "string")
    .slice(0, fallbackOptions.length);
  return labels.length === fallbackOptions.length ? labels : fallbackOptions;
}

export function isQuizOptionDisabled(feedback, exercise, feedbackState, isAnswerPending) {
  if (isAnswerPending && !isResolvedQuizFeedback(feedback, exercise)) return true;
  return isResolvedQuizFeedback(feedback, exercise) && !feedbackState;
}

export function readQuizOptionLabel(feedback, exercise, index, fallback) {
  if (!isQuizFeedbackVisible(feedback, exercise)) return fallback;
  return feedback.optionLabels[index] || fallback;
}

export function readQuizOptionFeedbackState(feedback, exercise, index, label) {
  if (!isResolvedQuizFeedback(feedback, exercise)) return null;
  const value = String(label || "");
  if (value.includes("✅")) return "correct";
  if (index === feedback.selectedIndex && value.includes("❌")) return "incorrect";
  return null;
}

export function quizOptionFeedbackSx(feedbackState) {
  if (feedbackState === "correct") {
    return {
      color: "success.main",
      borderColor: "success.main",
      bgcolor: "rgba(92, 200, 167, 0.12)",
    };
  }
  if (feedbackState === "incorrect") {
    return {
      color: "error.main",
      borderColor: "error.main",
      bgcolor: "rgba(255, 129, 119, 0.12)",
    };
  }
  return {};
}

export function parseProgressRows(progressBar) {
  const value = String(progressBar || "");
  const lines = value.split("\n").map((line) => line.trim()).filter(Boolean);
  const sourceLines = lines.length ? lines : [value];
  return sourceLines
    .map((line) => {
      const inside = line.match(/\[(.*)\]/)?.[1] || line;
      return inside.split("").filter((symbol) => ["✓", "●", "○", "✗", "⋯"].includes(symbol));
    })
    .filter((row) => row.length > 0);
}

export function progressSymbolLabel(symbol) {
  if (symbol === "⋯") return "\u00A0";
  if (symbol === "✗") return "×";
  return symbol;
}

export function progressSymbolColor(symbol) {
  if (symbol === "⋯") return "transparent";
  if (symbol === "✓") return "success.main";
  if (symbol === "✗") return "error.main";
  if (symbol === "●") return "primary.main";
  return "text.disabled";
}

export function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function isQuizFeedbackVisible(feedback, exercise) {
  return feedback?.sessionWordId === exercise.session_word_id;
}

function isResolvedQuizFeedback(feedback, exercise) {
  return isQuizFeedbackVisible(feedback, exercise) && feedback.isResolved;
}
