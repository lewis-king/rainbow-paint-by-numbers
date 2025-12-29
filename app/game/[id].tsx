import React, { useEffect, useState, useCallback, useRef } from 'react';
import { View, StyleSheet, ActivityIndicator, AppState, AppStateStatus } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { GameCanvas, GameCanvasHandle } from '@/components/GameCanvas';
import { PaletteBar } from '@/components/PaletteBar';
import { ToolBar } from '@/components/ToolBar';
import { HeaderBar } from '@/components/HeaderBar';
import { VictoryOverlay } from '@/components/VictoryOverlay';

import { loadLevelAssets, type LevelAssets } from '@/utils/level-loader';
import { useGameStore } from '@/store/game-store';
import { useLevelProgressStore } from '@/store/level-progress-store';
import { savePreview, deletePreview } from '@/utils/preview-manager';

export default function GameScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const canvasRef = useRef<GameCanvasHandle>(null);
  const [levelAssets, setLevelAssets] = useState<LevelAssets | null>(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [showVictory, setShowVictory] = useState(false);
  const [initialPaintedPixels, setInitialPaintedPixels] = useState<number[] | undefined>(undefined);

  const { reset, isComplete } = useGameStore();
  const { getLevelProgress, saveLevelProgress, resetLevel, isLevelComplete, _hasHydrated } = useLevelProgressStore();

  // Refs for debounced saving
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedProgressRef = useRef<number>(0);

  // Load level assets and saved progress
  useEffect(() => {
    if (!id || !_hasHydrated) return;

    setLoading(true);

    // Load saved progress for this level
    const savedProgress = getLevelProgress(id);
    if (savedProgress) {
      setProgress(savedProgress.progress);
      setInitialPaintedPixels(savedProgress.paintedPixels);
      lastSavedProgressRef.current = savedProgress.progress;
      if (savedProgress.isComplete) {
        setShowVictory(true);
      }
    } else {
      setProgress(0);
      setInitialPaintedPixels(undefined);
      lastSavedProgressRef.current = 0;
      setShowVictory(false);
    }

    loadLevelAssets(id).then((assets) => {
      setLevelAssets(assets);
      setLoading(false);
    });

    // Reset tool state (but not level progress)
    reset();
  }, [id, reset, getLevelProgress, _hasHydrated]);

  // Debounced save function
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedProgressRef = useRef<number>(0);

  const saveCurrentProgress = useCallback(() => {
    if (!id || !canvasRef.current) return;

    const paintedPixels = canvasRef.current.getPaintedPixels();
    const currentProgress = useGameStore.getState().progress;
    const complete = currentProgress >= 98;

    saveLevelProgress(id, currentProgress, complete, paintedPixels);
    lastSavedProgressRef.current = currentProgress;

    // Save preview image
    const snapshot = canvasRef.current.getCanvasSnapshot();
    if (snapshot) {
      savePreview(id, snapshot);
    }
  }, [id, saveLevelProgress]);

  // Save progress when it changes (debounced)
  useEffect(() => {
    // Don't save if progress hasn't actually changed
    if (progress === lastSavedProgressRef.current || progress === 0) return;

    // Clear existing timeout
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    // Debounce save by 500ms
    saveTimeoutRef.current = setTimeout(() => {
      saveCurrentProgress();
    }, 500);

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [progress, saveCurrentProgress]);

  // Save when app goes to background
  useEffect(() => {
    const handleAppStateChange = (nextAppState: AppStateStatus) => {
      if (nextAppState === 'background' || nextAppState === 'inactive') {
        saveCurrentProgress();
      }
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription.remove();
  }, [saveCurrentProgress]);

  // Also save on unmount as a fallback
  useEffect(() => {
    return () => {
      saveCurrentProgress();
    };
  }, [saveCurrentProgress]);

  // Handle victory
  useEffect(() => {
    if (isComplete && !showVictory) {
      setShowVictory(true);
    }
  }, [isComplete, showVictory]);

  const handleProgressChange = useCallback((newProgress: number) => {
    setProgress(newProgress);
    useGameStore.getState().setProgress(newProgress);
  }, []);

  const handleReset = useCallback(() => {
    if (id) {
      resetLevel(id);
      deletePreview(id);
    }
    reset();
    setProgress(0);
    setShowVictory(false);
    setInitialPaintedPixels(undefined);
    // Force re-mount of canvas by toggling loading
    setLoading(true);
    setTimeout(() => setLoading(false), 100);
  }, [reset, resetLevel, id]);

  if (loading || !levelAssets) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#fff" />
      </View>
    );
  }

  return (
    <GestureHandlerRootView style={styles.container}>
      <View style={styles.container}>
        <HeaderBar progress={progress} onReset={handleReset} />

        <View style={styles.canvasContainer}>
          <GameCanvas
            ref={canvasRef}
            levelData={levelAssets.data}
            linesUri={levelAssets.linesUri}
            mapUri={levelAssets.mapUri}
            onProgressChange={handleProgressChange}
            initialPaintedPixels={initialPaintedPixels}
          />
        </View>

        <View style={[styles.bottomUI, { paddingBottom: Math.max(insets.bottom, 12) }]}>
          <ToolBar />
          <PaletteBar palette={levelAssets.data.palette} />
        </View>

        <VictoryOverlay
          rewardUri={levelAssets.rewardUri}
          visible={showVictory}
          onReset={handleReset}
        />
      </View>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a2e',
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: '#1a1a2e',
    justifyContent: 'center',
    alignItems: 'center',
  },
  canvasContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  bottomUI: {
    gap: 8,
  },
});
