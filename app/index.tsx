import { useState, useEffect } from 'react';
import { View, Text, StyleSheet, Pressable, Dimensions, ActivityIndicator, ScrollView } from 'react-native';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  FadeIn,
} from 'react-native-reanimated';
import MaskedView from '@react-native-masked-view/masked-view';
import { LinearGradient } from 'expo-linear-gradient';

import { getLevelPreviews, type LevelPreview } from '@/utils/level-loader';
import { useLevelProgressStore } from '@/store/level-progress-store';
import { getPreviewPath, previewExists } from '@/utils/preview-manager';
import { colors, fonts, shadows, rainbowArray } from '@/theme';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const GRID_PADDING = 20;
const GRID_GAP = 16;
const COLUMNS = 2;
const CARD_SIZE = (SCREEN_WIDTH - GRID_PADDING * 2 - GRID_GAP * (COLUMNS - 1)) / COLUMNS;

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

// Rainbow gradient title with subtle color cycling
function RainbowTitle() {
  const [colorOffset, setColorOffset] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setColorOffset((prev) => (prev + 1) % rainbowArray.length);
    }, 2000); // Shift colors every 2 seconds
    return () => clearInterval(interval);
  }, []);

  // Rotate the rainbow colors based on offset
  const shiftedColors = [
    ...rainbowArray.slice(colorOffset),
    ...rainbowArray.slice(0, colorOffset),
  ];

  return (
    <MaskedView
      maskElement={
        <View style={styles.titleMaskContainer}>
          <Text style={styles.titleMask}>Rainbow</Text>
          <Text style={styles.titleMaskSmall}>Paint by Numbers</Text>
        </View>
      }
    >
      <LinearGradient
        colors={shiftedColors}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 0.5 }}
        style={styles.titleGradient}
      />
    </MaskedView>
  );
}

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const levels = getLevelPreviews();
  const { isLevelComplete, getLevelProgress, _hasHydrated } = useLevelProgressStore();

  const handleLevelPress = (levelId: string) => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    router.push(`/game/${levelId}`);
  };

  // Wait for store to hydrate from AsyncStorage
  if (!_hasHydrated) {
    return (
      <View style={[styles.container, styles.loadingContainer, { paddingTop: insets.top + 20 }]}>
        <ActivityIndicator size="large" color={colors.rainbow.blue} />
      </View>
    );
  }

  return (
    <View style={[styles.container, { paddingTop: insets.top + 16 }]}>
      {/* Rainbow Title */}
      <Animated.View
        entering={FadeIn.delay(100).duration(400)}
        style={styles.titleContainer}
      >
        <RainbowTitle />
      </Animated.View>

      <ScrollView
        contentContainerStyle={[styles.grid, { paddingBottom: Math.max(insets.bottom, GRID_PADDING) }]}
        showsVerticalScrollIndicator={false}
      >
        {levels.map((level, index) => {
          const savedProgress = getLevelProgress(level.id);
          const isComplete = isLevelComplete(level.id);
          const progressPercent = savedProgress?.progress ?? 0;
          const lastUpdated = savedProgress?.lastUpdated;

          return (
            <LevelCard
              key={level.id}
              level={level}
              index={index}
              isComplete={isComplete}
              progressPercent={progressPercent}
              lastUpdated={lastUpdated}
              onPress={() => handleLevelPress(level.id)}
            />
          );
        })}
      </ScrollView>
    </View>
  );
}

interface LevelCardProps {
  level: LevelPreview;
  index: number;
  isComplete: boolean;
  progressPercent: number;
  lastUpdated?: number;
  onPress: () => void;
}

function LevelCard({ level, index, isComplete, progressPercent, lastUpdated, onPress }: LevelCardProps) {
  const [hasPreview, setHasPreview] = useState(false);
  const [previewPath, setPreviewPath] = useState<string | null>(null);
  const scale = useSharedValue(1);

  // Check if preview exists when progress changes
  useEffect(() => {
    let mounted = true;

    async function checkPreview() {
      if (progressPercent > 0) {
        const exists = await previewExists(level.id);
        if (mounted) {
          setHasPreview(exists);
          if (exists) {
            // Add timestamp as cache buster to force reload when preview changes
            const basePath = getPreviewPath(level.id);
            setPreviewPath(lastUpdated ? `${basePath}?t=${lastUpdated}` : basePath);
          }
        }
      } else {
        setHasPreview(false);
        setPreviewPath(null);
      }
    }

    checkPreview();
    return () => { mounted = false; };
  }, [level.id, progressPercent, lastUpdated]);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: withSpring(scale.value, { damping: 12 }) }],
  }));

  const handlePressIn = () => {
    scale.value = 0.95;
  };

  const handlePressOut = () => {
    scale.value = 1;
  };

  // For completed levels, show the original colored image
  // For in-progress levels with preview, show the preview
  // Otherwise show the lines thumbnail
  const imageSource = isComplete
    ? level.originalSource
    : hasPreview && previewPath
      ? { uri: previewPath }
      : level.thumbnailSource;

  // Rainbow border color for completed levels
  const borderColor = isComplete ? rainbowArray[index % rainbowArray.length] : 'transparent';

  return (
    <AnimatedPressable
      style={[styles.card, animatedStyle, { borderColor }]}
      onPress={onPress}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      entering={FadeIn.delay(150 + index * 100).duration(400)}
    >
      <Image
        source={imageSource}
        style={styles.thumbnail}
        contentFit="cover"
      />

      {/* Progress bar for in-progress levels */}
      {progressPercent > 0 && !isComplete && (
        <View style={styles.progressBarContainer}>
          <View
            style={[
              styles.progressBar,
              {
                width: `${progressPercent}%`,
                backgroundColor: rainbowArray[Math.floor((progressPercent / 100) * (rainbowArray.length - 1))],
              },
            ]}
          />
        </View>
      )}

      {/* Completion indicator */}
      {isComplete && (
        <View style={[styles.completeBadge, { backgroundColor: borderColor }]}>
          <Ionicons name="star" size={24} color={colors.celebration.gold} />
        </View>
      )}
    </AnimatedPressable>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.backgrounds.primary,
  },
  loadingContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  titleContainer: {
    alignItems: 'center',
    paddingBottom: 12,
  },
  titleMaskContainer: {
    alignItems: 'center',
  },
  titleMask: {
    fontFamily: fonts.heading,
    fontSize: 38,
    fontWeight: 'bold',
    color: 'black', // Color is used as mask - black = visible
    textAlign: 'center',
  },
  titleMaskSmall: {
    fontFamily: fonts.heading,
    fontSize: 22,
    fontWeight: 'bold',
    color: 'black',
    textAlign: 'center',
    marginTop: -4,
  },
  titleGradient: {
    height: 80,
    width: SCREEN_WIDTH,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    padding: GRID_PADDING,
    gap: GRID_GAP,
  },
  card: {
    width: CARD_SIZE,
    height: CARD_SIZE,
    borderRadius: 24,
    overflow: 'hidden',
    backgroundColor: colors.backgrounds.card,
    borderWidth: 4,
    ...shadows.medium,
  },
  thumbnail: {
    width: '100%',
    height: '100%',
  },
  progressBarContainer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    height: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.4)',
  },
  progressBar: {
    height: '100%',
    borderRadius: 4,
  },
  completeBadge: {
    position: 'absolute',
    top: 10,
    right: 10,
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    ...shadows.small,
  },
});
