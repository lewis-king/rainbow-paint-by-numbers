import { useEffect } from 'react';
import { AppState, Platform } from 'react-native';
import { useReviewStore } from '@/store/review-store';
import { useIsFocused } from '@react-navigation/native';

/** The stores own rating UI. Never display sample ratings or a sentiment gate. */
export function ReviewPrompt({ visible, onClose }: {
  visible: boolean;
  onClose: () => void;
}) {
  const isFocused = useIsFocused();
  useEffect(() => {
    if (!visible || !isFocused) return;
    let cancelled = false;
    const canPresent = () => !cancelled && Platform.OS !== 'web' && AppState.currentState === 'active';
    const timer = setTimeout(() => {
      if (Platform.OS === 'web' || AppState.currentState !== 'active') {
        onClose();
        return;
      }
      void useReviewStore.getState().requestReview(canPresent).finally(() => {
        if (!cancelled) onClose();
      });
    }, 1000);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [visible, isFocused, onClose]);
  return null;
}

export default ReviewPrompt;
