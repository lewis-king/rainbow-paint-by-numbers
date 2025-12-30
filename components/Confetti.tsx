import React, { useEffect, useMemo } from 'react';
import { View, StyleSheet, Dimensions } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withDelay,
  withSequence,
  withSpring,
  Easing,
  interpolate,
  runOnJS,
} from 'react-native-reanimated';
import { rainbowArray, celebration } from '@/theme';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// Star shapes and colors
const STAR_COLORS = [...rainbowArray, celebration.gold, celebration.sparkle, celebration.pink];
const PARTICLE_COUNT = 50;

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  color: string;
  rotation: number;
  delay: number;
  duration: number;
  type: 'star' | 'circle' | 'sparkle';
}

function generateParticles(): Particle[] {
  return Array.from({ length: PARTICLE_COUNT }, (_, i) => {
    const angle = (i / PARTICLE_COUNT) * Math.PI * 2;
    const distance = 100 + Math.random() * 200;

    return {
      id: i,
      x: Math.cos(angle) * distance,
      y: Math.sin(angle) * distance - 100, // Bias upward
      size: 8 + Math.random() * 16,
      color: STAR_COLORS[Math.floor(Math.random() * STAR_COLORS.length)],
      rotation: Math.random() * 360,
      delay: Math.random() * 300,
      duration: 800 + Math.random() * 400,
      type: ['star', 'circle', 'sparkle'][Math.floor(Math.random() * 3)] as Particle['type'],
    };
  });
}

interface StarParticleProps {
  particle: Particle;
  trigger: boolean;
}

function StarParticle({ particle, trigger }: StarParticleProps) {
  const progress = useSharedValue(0);
  const opacity = useSharedValue(0);

  useEffect(() => {
    if (trigger) {
      progress.value = 0;
      opacity.value = 0;

      progress.value = withDelay(
        particle.delay,
        withTiming(1, { duration: particle.duration, easing: Easing.out(Easing.cubic) })
      );

      opacity.value = withDelay(
        particle.delay,
        withSequence(
          withTiming(1, { duration: 150 }),
          withDelay(particle.duration - 400, withTiming(0, { duration: 250 }))
        )
      );
    }
  }, [trigger]);

  const animatedStyle = useAnimatedStyle(() => {
    const translateX = interpolate(progress.value, [0, 1], [0, particle.x]);
    const translateY = interpolate(progress.value, [0, 1], [0, particle.y]);
    const scale = interpolate(progress.value, [0, 0.2, 0.8, 1], [0, 1.2, 1, 0.5]);
    const rotate = interpolate(progress.value, [0, 1], [0, particle.rotation]);

    return {
      transform: [
        { translateX },
        { translateY },
        { scale },
        { rotate: `${rotate}deg` },
      ],
      opacity: opacity.value,
    };
  });

  const renderShape = () => {
    const shapeStyle = {
      width: particle.size,
      height: particle.size,
      backgroundColor: particle.color,
    };

    switch (particle.type) {
      case 'star':
        return <Star size={particle.size} color={particle.color} />;
      case 'sparkle':
        return <Sparkle size={particle.size} color={particle.color} />;
      default:
        return <View style={[styles.circle, shapeStyle]} />;
    }
  };

  return (
    <Animated.View style={[styles.particle, animatedStyle]}>
      {renderShape()}
    </Animated.View>
  );
}

// 4-pointed star shape
function Star({ size, color }: { size: number; color: string }) {
  return (
    <View style={[styles.starContainer, { width: size, height: size }]}>
      <View style={[styles.starPoint, styles.starVertical, { backgroundColor: color, height: size, width: size * 0.35 }]} />
      <View style={[styles.starPoint, styles.starHorizontal, { backgroundColor: color, width: size, height: size * 0.35 }]} />
    </View>
  );
}

// Sparkle/diamond shape
function Sparkle({ size, color }: { size: number; color: string }) {
  return (
    <View
      style={[
        styles.sparkle,
        {
          width: size,
          height: size,
          backgroundColor: color,
          transform: [{ rotate: '45deg' }],
        },
      ]}
    />
  );
}

interface ConfettiProps {
  visible: boolean;
  onComplete?: () => void;
}

export function Confetti({ visible, onComplete }: ConfettiProps) {
  const particles = useMemo(() => generateParticles(), [visible]);

  useEffect(() => {
    if (visible && onComplete) {
      const timer = setTimeout(onComplete, 1500);
      return () => clearTimeout(timer);
    }
  }, [visible, onComplete]);

  if (!visible) return null;

  return (
    <View style={styles.container} pointerEvents="none">
      <View style={styles.center}>
        {particles.map((particle) => (
          <StarParticle key={particle.id} particle={particle} trigger={visible} />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 200,
  },
  center: {
    position: 'absolute',
    top: SCREEN_HEIGHT * 0.35,
    left: SCREEN_WIDTH / 2,
  },
  particle: {
    position: 'absolute',
  },
  circle: {
    borderRadius: 999,
  },
  starContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  starPoint: {
    position: 'absolute',
    borderRadius: 2,
  },
  starVertical: {},
  starHorizontal: {},
  sparkle: {
    borderRadius: 2,
  },
});

export default Confetti;
