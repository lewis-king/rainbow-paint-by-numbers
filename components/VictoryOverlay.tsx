import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, Pressable, Animated, Dimensions } from 'react-native';
import { useVideoPlayer, VideoView } from 'expo-video';
import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

interface VictoryOverlayProps {
  rewardUri?: string;
  visible: boolean;
  onReset: () => void;
}

export function VictoryOverlay({ rewardUri, visible, onReset }: VictoryOverlayProps) {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.8)).current;

  const player = useVideoPlayer(rewardUri ?? null, (player) => {
    player.loop = true;
  });

  useEffect(() => {
    if (visible) {
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 1,
          duration: 500,
          useNativeDriver: true,
        }),
        Animated.spring(scaleAnim, {
          toValue: 1,
          friction: 8,
          tension: 40,
          useNativeDriver: true,
        }),
      ]).start();

      // Start playing when visible
      if (player) {
        player.play();
      }
    } else {
      fadeAnim.setValue(0);
      scaleAnim.setValue(0.8);

      // Pause when hidden
      if (player) {
        player.pause();
      }
    }
  }, [visible, fadeAnim, scaleAnim, player]);

  if (!visible) return null;

  const handleBackToGallery = () => {
    router.back();
  };

  return (
    <Animated.View style={[styles.overlay, { opacity: fadeAnim }]}>
      <Animated.View style={[styles.content, { transform: [{ scale: scaleAnim }] }]}>
        {rewardUri && player ? (
          <VideoView
            player={player}
            style={styles.video}
            contentFit="contain"
            nativeControls={false}
          />
        ) : (
          <View style={styles.fallbackCelebration}>
            <Ionicons name="star" size={100} color="#FFD700" />
          </View>
        )}

        <View style={styles.buttonRow}>
          <Pressable style={styles.actionButton} onPress={onReset}>
            <Ionicons name="refresh" size={32} color="#fff" />
          </Pressable>
          <Pressable style={[styles.actionButton, styles.homeButton]} onPress={handleBackToGallery}>
            <Ionicons name="home" size={32} color="#fff" />
          </Pressable>
        </View>
      </Animated.View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 100,
  },
  content: {
    width: SCREEN_WIDTH * 0.9,
    height: SCREEN_HEIGHT * 0.7,
    borderRadius: 24,
    overflow: 'hidden',
    backgroundColor: '#1a1a2e',
    justifyContent: 'center',
    alignItems: 'center',
  },
  video: {
    width: '100%',
    height: '80%',
  },
  fallbackCelebration: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  buttonRow: {
    position: 'absolute',
    bottom: 20,
    flexDirection: 'row',
    gap: 20,
  },
  actionButton: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#3d3d5c',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
  },
  homeButton: {
    backgroundColor: '#4CAF50',
  },
});
