export enum MomoState {
  DEFAULT = 'default',       // Resting (closed mouth)
  HAPPY = 'happy',          // User is typing (waiting happily)
  MOUTH_OPEN = 'mouth_open', // Ready to eat (hovering)
  CHEWING = 'chewing',      // Processing (chewing animation)
  SUCCESS = 'success',      // Processing complete (mouth open + sparkles)
}
