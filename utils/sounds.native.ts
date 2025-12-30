/**
 * Sound effects manager for Rainbow Paint by Numbers (Native)
 *
 * Celebratory sounds to make painting magical!
 */

import { createAudioPlayer, AudioPlayer } from 'expo-audio';

const celebrationAsset = require('../assets/sounds/celebration.mp3');
const popAsset = require('../assets/sounds/pop.mp3');

let celebrationPlayer: AudioPlayer | null = null;
let popPlayer: AudioPlayer | null = null;

/**
 * Play the celebration fanfare
 */
export async function playCelebration(): Promise<void> {
  try {
    if (!celebrationPlayer) {
      celebrationPlayer = createAudioPlayer(celebrationAsset);
    }
    celebrationPlayer.seekTo(0);
    celebrationPlayer.volume = 0.8;
    celebrationPlayer.play();
  } catch (e) {
    console.warn('Failed to play celebration:', e);
  }
}

/**
 * Play a pop sound (for UI interactions)
 */
export async function playPop(): Promise<void> {
  try {
    if (!popPlayer) {
      popPlayer = createAudioPlayer(popAsset);
    }
    popPlayer.seekTo(0);
    popPlayer.volume = 0.5;
    popPlayer.play();
  } catch (e) {
    console.warn('Failed to play pop:', e);
  }
}

/**
 * Preload sounds for instant playback
 */
export async function preloadSounds(): Promise<void> {
  try {
    celebrationPlayer = createAudioPlayer(celebrationAsset);
    popPlayer = createAudioPlayer(popAsset);
  } catch (e) {
    console.warn('Failed to preload sounds:', e);
  }
}

/**
 * Cleanup sounds on app unmount
 */
export async function unloadSounds(): Promise<void> {
  celebrationPlayer?.remove();
  popPlayer?.remove();
  celebrationPlayer = null;
  popPlayer = null;
}
