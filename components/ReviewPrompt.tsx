import React from 'react';
import { View, Text, StyleSheet, Pressable, Modal, Dimensions } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useReviewStore } from '@/store/review-store';
import { colors, fonts } from '@/theme';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

interface ReviewPromptProps {
  visible: boolean;
  onClose: () => void;
}

export function ReviewPrompt({ visible, onClose }: ReviewPromptProps) {
  const { requestReview } = useReviewStore();

  const handleRequestReview = async () => {
    await requestReview();
    onClose();
  };

  const handleMaybeLater = () => {
    // Just close - the store handles the 7-day cooldown
    onClose();
  };

  const handleNeverAsk = () => {
    // Mark as clicked review to never show again
    useReviewStore.getState().markClickedReview();
    onClose();
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.container}>
          {/* Header with stars */}
          <View style={styles.header}>
            <Text style={styles.title}>Love the app?</Text>
            <View style={styles.starsRow}>
              <Ionicons name="star" size={20} color={colors.rainbow.red} />
              <Ionicons name="star" size={20} color={colors.rainbow.orange} />
              <Ionicons name="star" size={20} color={colors.rainbow.yellow} />
              <Ionicons name="star" size={20} color={colors.rainbow.green} />
              <Ionicons name="star" size={20} color={colors.rainbow.blue} />
            </View>
          </View>

          {/* Message */}
          <Text style={styles.message}>
            We'd love your feedback to help us improve Rainbow Paint!
          </Text>

          {/* Action Buttons */}
          <View style={styles.buttonStack}>
            <Pressable
              style={[styles.button, styles.reviewButton]}
              onPress={handleRequestReview}
            >
              <Ionicons name="star-outline" size={20} color={colors.backgrounds.primary} />
              <Text style={styles.reviewButtonText}>
                Leave a Review
              </Text>
            </Pressable>

            <Pressable
              style={[styles.button, styles.laterButton]}
              onPress={handleMaybeLater}
            >
              <Text style={styles.laterButtonText}>
                Maybe Later
              </Text>
            </Pressable>

            <Pressable
              style={styles.neverButton}
              onPress={handleNeverAsk}
            >
              <Text style={styles.neverButtonText}>Don't Ask Again</Text>
            </Pressable>
          </View>

          {/* Reassurance */}
          <Text style={styles.reassurance}>
            No ads, no paywalls — just pure coloring fun! 🎨
          </Text>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  container: {
    width: SCREEN_WIDTH * 0.85,
    backgroundColor: colors.backgrounds.primary,
    borderRadius: 24,
    padding: 24,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 8,
  },
  header: {
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontFamily: fonts.heading,
    fontSize: 24,
    color: colors.text.primary,
    marginBottom: 8,
  },
  starsRow: {
    flexDirection: 'row',
    gap: 4,
  },
  message: {
    fontSize: 16,
    color: colors.text.secondary,
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 24,
  },
  buttonStack: {
    width: '100%',
    gap: 12,
  },
  button: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 12,
    gap: 8,
  },
  reviewButton: {
    backgroundColor: colors.rainbow.indigo,
  },
  reviewButtonText: {
    fontFamily: fonts.body,
    fontSize: 16,
    fontWeight: '600',
    color: colors.backgrounds.primary,
  },
  laterButton: {
    backgroundColor: colors.backgrounds.card,
  },
  laterButtonText: {
    fontFamily: fonts.body,
    fontSize: 16,
    color: colors.text.primary,
  },
  neverButton: {
    paddingVertical: 8,
  },
  neverButtonText: {
    fontFamily: fonts.body,
    fontSize: 14,
    color: colors.text.secondary,
    textAlign: 'center',
  },
  reassurance: {
    marginTop: 16,
    fontSize: 12,
    color: colors.text.secondary,
    textAlign: 'center',
    fontStyle: 'italic',
  },
});

export default ReviewPrompt;
