import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Pressable, Dimensions } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withSpring,
  withSequence,
  withDelay,
  withRepeat,
  Easing,
  interpolateColor,
} from 'react-native-reanimated';
import { useVideoPlayer, VideoView } from 'expo-video';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import * as Haptics from 'expo-haptics';

import { Confetti } from './Confetti';
import { playCelebration, playPop } from '@/utils/sounds';
import { colors, fonts, rainbowArray } from '@/theme';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

interface VictoryOverlayProps {
  rewardUri?: string;
  visible: boolean;
  onReset: () => void;
}

export function VictoryOverlay({ rewardUri, visible, onReset }: VictoryOverlayProps) {
  const [showConfetti, setShowConfetti] = useState(false);
  const fadeAnim = useSharedValue(0);

  // Video player for reward animation
  const player = useVideoPlayer(rewardUri ?? null, (p) => {
    p.loop = true;
    p.muted = true;
  });
  const scaleAnim = useSharedValue(0.5);
  const titleScale = useSharedValue(0);
  const rainbowProgress = useSharedValue(0);
  const buttonScale1 = useSharedValue(0);
  const buttonScale2 = useSharedValue(0);

  useEffect(() => {
    if (visible) {
      // Reset animations
      fadeAnim.value = 0;
      scaleAnim.value = 0.5;
      titleScale.value = 0;
      buttonScale1.value = 0;
      buttonScale2.value = 0;

      // Play reward video
      player.play();

      // Trigger celebration sequence
      setShowConfetti(true);
      playCelebration();
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);

      // Animate in
      fadeAnim.value = withTiming(1, { duration: 400 });

      scaleAnim.value = withSpring(1, {
        damping: 12,
        stiffness: 100,
      });

      // Title bounces in after container
      titleScale.value = withDelay(
        200,
        withSequence(
          withSpring(1.2, { damping: 8, stiffness: 150 }),
          withSpring(1, { damping: 10 })
        )
      );

      // Rainbow border animation
      rainbowProgress.value = withRepeat(
        withTiming(1, { duration: 3000, easing: Easing.linear }),
        -1, // infinite
        false
      );

      // Buttons pop in sequentially
      buttonScale1.value = withDelay(400, withSpring(1, { damping: 10 }));
      buttonScale2.value = withDelay(500, withSpring(1, { damping: 10 }));
    } else {
      setShowConfetti(false);
      player.pause();
      fadeAnim.value = 0;
      scaleAnim.value = 0.5;
      titleScale.value = 0;
      rainbowProgress.value = 0;
      buttonScale1.value = 0;
      buttonScale2.value = 0;
    }
  }, [visible, player]);

  const overlayStyle = useAnimatedStyle(() => ({
    opacity: fadeAnim.value,
  }));

  const containerStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scaleAnim.value }],
  }));

  const titleStyle = useAnimatedStyle(() => ({
    transform: [{ scale: titleScale.value }],
  }));

  // Rainbow border animation
  const borderStyle = useAnimatedStyle(() => {
    const color = interpolateColor(
      rainbowProgress.value,
      [0, 0.14, 0.28, 0.42, 0.56, 0.7, 0.84, 1],
      [...rainbowArray, rainbowArray[0]]
    );
    return {
      borderColor: color,
      shadowColor: color,
    };
  });

  const button1Style = useAnimatedStyle(() => ({
    transform: [{ scale: buttonScale1.value }],
  }));

  const button2Style = useAnimatedStyle(() => ({
    transform: [{ scale: buttonScale2.value }],
  }));

  if (!visible) return null;

  const handleBackToGallery = () => {
    playPop();
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    router.back();
  };

  const handleReset = () => {
    playPop();
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onReset();
  };

  return (
    <Animated.View style={[styles.overlay, overlayStyle]}>
      <Confetti visible={showConfetti} />

      <Animated.View style={[styles.content, containerStyle, borderStyle]}>
        {/* Celebration Title */}
        <Animated.View style={[styles.titleContainer, titleStyle]}>
          <Text style={styles.title}>Amazing!</Text>
          <View style={styles.starsRow}>
            <Ionicons name="star" size={24} color={colors.celebration.gold} />
            <Ionicons name="star" size={32} color={colors.celebration.gold} />
            <Ionicons name="star" size={24} color={colors.celebration.gold} />
          </View>
        </Animated.View>

        {/* Reward Video */}
        <View style={styles.videoContainer}>
          <VideoView
            player={player}
            style={styles.rewardVideo}
            contentFit="contain"
            nativeControls={false}
          />
        </View>

        {/* Action Buttons */}
        <View style={styles.buttonRow}>
          <Animated.View style={button1Style}>
            <Pressable
              style={({ pressed }) => [
                styles.actionButton,
                styles.replayButton,
                pressed && styles.buttonPressed,
              ]}
              onPress={handleReset}
            >
              <Ionicons name="refresh" size={28} color="#fff" />
              <Text style={styles.buttonText}>Again!</Text>
            </Pressable>
          </Animated.View>

          <Animated.View style={button2Style}>
            <Pressable
              style={({ pressed }) => [
                styles.actionButton,
                styles.homeButton,
                pressed && styles.buttonPressed,
              ]}
              onPress={handleBackToGallery}
            >
              <Ionicons name="home" size={28} color="#fff" />
              <Text style={styles.buttonText}>Home</Text>
            </Pressable>
          </Animated.View>
        </View>
      </Animated.View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: colors.backgrounds.overlay,
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 100,
  },
  content: {
    width: SCREEN_WIDTH * 0.9,
    height: SCREEN_HEIGHT * 0.75,
    borderRadius: 32,
    overflow: 'hidden',
    backgroundColor: colors.backgrounds.primary,
    alignItems: 'center',
    paddingVertical: 16,
    borderWidth: 4,
    // Shadow for glow effect
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 20,
    elevation: 10,
  },
  titleContainer: {
    alignItems: 'center',
    paddingTop: 8,
    paddingBottom: 12,
  },
  title: {
    fontFamily: fonts.heading,
    fontSize: 42,
    color: colors.celebration.gold,
    textShadowColor: 'rgba(255, 215, 0, 0.5)',
    textShadowOffset: { width: 0, height: 2 },
    textShadowRadius: 10,
  },
  starsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: 4,
  },
  videoContainer: {
    flex: 1,
    width: '100%',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
  },
  rewardVideo: {
    width: '100%',
    height: '100%',
    borderRadius: 16,
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 20,
    paddingBottom: 8,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 50,
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  replayButton: {
    backgroundColor: colors.rainbow.orange,
  },
  homeButton: {
    backgroundColor: colors.rainbow.green,
  },
  buttonPressed: {
    transform: [{ scale: 0.95 }],
    opacity: 0.9,
  },
  buttonText: {
    fontFamily: fonts.bodyBold,
    fontWeight: 'bold' as const,
    fontSize: 16,
    color: '#fff',
  },
});

export default VictoryOverlay;
