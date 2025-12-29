import { useState, useEffect } from 'react';
import { View, StyleSheet, Pressable, Dimensions, ActivityIndicator } from 'react-native';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { getLevelPreviews, type LevelPreview } from '@/utils/level-loader';
import { useLevelProgressStore } from '@/store/level-progress-store';
import { getPreviewPath, previewExists } from '@/utils/preview-manager';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const GRID_PADDING = 20;
const GRID_GAP = 16;
const COLUMNS = 2;
const CARD_SIZE = (SCREEN_WIDTH - GRID_PADDING * 2 - GRID_GAP * (COLUMNS - 1)) / COLUMNS;

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const levels = getLevelPreviews();
  const { isLevelComplete, getLevelProgress, _hasHydrated } = useLevelProgressStore();

  const handleLevelPress = (levelId: string) => {
    router.push(`/game/${levelId}`);
  };

  // Wait for store to hydrate from AsyncStorage
  if (!_hasHydrated) {
    return (
      <View style={[styles.container, styles.loadingContainer, { paddingTop: insets.top + 20 }]}>
        <ActivityIndicator size="large" color="#fff" />
      </View>
    );
  }

  return (
    <View style={[styles.container, { paddingTop: insets.top + 20 }]}>
      <View style={[styles.grid, { paddingBottom: Math.max(insets.bottom, GRID_PADDING) }]}>
        {levels.map((level) => {
          const savedProgress = getLevelProgress(level.id);
          const isComplete = isLevelComplete(level.id);
          const progressPercent = savedProgress?.progress ?? 0;

          return (
            <LevelCard
              key={level.id}
              level={level}
              isComplete={isComplete}
              progressPercent={progressPercent}
              onPress={() => handleLevelPress(level.id)}
            />
          );
        })}
      </View>
    </View>
  );
}

interface LevelCardProps {
  level: LevelPreview;
  isComplete: boolean;
  progressPercent: number;
  onPress: () => void;
}

function LevelCard({ level, isComplete, progressPercent, onPress }: LevelCardProps) {
  const [hasPreview, setHasPreview] = useState(false);
  const [previewPath, setPreviewPath] = useState<string | null>(null);

  // Check if preview exists when progress changes
  useEffect(() => {
    let mounted = true;

    async function checkPreview() {
      if (progressPercent > 0) {
        const exists = await previewExists(level.id);
        if (mounted) {
          setHasPreview(exists);
          if (exists) {
            setPreviewPath(getPreviewPath(level.id));
          }
        }
      } else {
        setHasPreview(false);
        setPreviewPath(null);
      }
    }

    checkPreview();
    return () => { mounted = false; };
  }, [level.id, progressPercent]);

  // Use preview if available, otherwise use original thumbnail
  const imageSource = hasPreview && previewPath
    ? { uri: previewPath }
    : level.thumbnailSource;

  return (
    <Pressable
      style={({ pressed }) => [
        styles.card,
        pressed && styles.cardPressed,
      ]}
      onPress={onPress}
    >
      <Image
        source={imageSource}
        style={styles.thumbnail}
        contentFit="cover"
      />

      {/* Progress bar for in-progress levels */}
      {progressPercent > 0 && !isComplete && (
        <View style={styles.progressBarContainer}>
          <View style={[styles.progressBar, { width: `${progressPercent}%` }]} />
        </View>
      )}

      {/* Completion indicator */}
      {isComplete && (
        <View style={styles.completeBadge}>
          <Ionicons name="checkmark-circle" size={36} color="#4CAF50" />
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a2e',
  },
  loadingContainer: {
    justifyContent: 'center',
    alignItems: 'center',
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
    borderRadius: 20,
    overflow: 'hidden',
    backgroundColor: '#2d2d44',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
  },
  cardPressed: {
    transform: [{ scale: 0.95 }],
    opacity: 0.9,
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
    height: 6,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  progressBar: {
    height: '100%',
    backgroundColor: '#4CAF50',
  },
  completeBadge: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 18,
    padding: 2,
  },
});
