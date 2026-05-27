export function playAudio(audioUrl) {
  if (!audioUrl) return;
  new Audio(audioUrl).play().catch(() => {});
}
