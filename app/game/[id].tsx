import React, { useEffect, useState, useCallback, useRef } from 'react';
import { View, StyleSheet, ActivityIndicator, AppState, AppStateStatus } from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useKeepAwake } from 'expo-keep-awake';

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
  useKeepAwake();
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const canvasRef = useRef<GameCanvasHandle>(null);
  const [levelAssets, setLevelAssets] = useState<LevelAssets | null>(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(0);
  const [showVictory, setShowVictory] = useState(false);
  const [initialPaintedPixels, setInitialPaintedPixels] = useState<number[] | undefined>(undefined);

  const reset = useGameStore((state) => state.reset);
  const { getLevelProgress, saveProgress, saveFullState, resetLevel, _hasHydrated } = useLevelProgressStore();

  // Refs for debounced saving
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastSavedProgressRef = useRef<number>(0);
  // Store latest snapshot and pixels for cleanup (since canvasRef may be null during unmount)
  const latestSnapshotRef = useRef<string | null>(null);
  const latestPaintedPixelsRef = useRef<Set<number>>(new Set());
  // Track if any painting happened this session (to avoid overwriting completed levels on unmount)
  const hasPaintedRef = useRef<boolean>(false);

  // Load level assets and saved progress
  useEffect(() => {
    if (!id || !_hasHydrated) return;

    // Reset tool state immediately to prevent stale isComplete from previous level
    reset();

    // Reset painting tracker for new level
    hasPaintedRef.current = false;

    setLoading(true);

    // Load saved progress for this level
    const savedProgress = getLevelProgress(id);
    if (savedProgress) {
      setProgress(savedProgress.progress);
      setInitialPaintedPixels(savedProgress.paintedPixels);
      lastSavedProgressRef.current = savedProgress.progress;
      // Pre-populate cache with saved data so it's available even if canvas unmounts before we can read it
      if (savedProgress.paintedPixels && savedProgress.paintedPixels.length > 0) {
        latestPaintedPixelsRef.current = new Set(savedProgress.paintedPixels);
      }
      // Only show victory if this level is actually complete
      setShowVictory(savedProgress.isComplete);
    } else {
      setProgress(0);
      setInitialPaintedPixels(undefined);
      lastSavedProgressRef.current = 0;
      latestPaintedPixelsRef.current = new Set();
      setShowVictory(false);
    }

    loadLevelAssets(id).then((assets) => {
      setLevelAssets(assets);
      setLoading(false);
    });
  }, [id, reset, getLevelProgress, _hasHydrated]);

  // Quick save - just progress percentage (no pixel data)
  const saveQuickProgress = useCallback(() => {
    if (!id) return;

    const currentProgress = useGameStore.getState().progress;
    const complete = currentProgress >= 98;

    saveProgress(id, currentProgress, complete);
    lastSavedProgressRef.current = currentProgress;
  }, [id, saveProgress]);

  // Update cached snapshot and pixels (called periodically during painting)
  const updateCachedData = useCallback(() => {
    if (!canvasRef.current) return;

    latestPaintedPixelsRef.current = canvasRef.current.getPaintedPixels();
    const snapshot = canvasRef.current.getCanvasSnapshot();
    if (snapshot) {
      latestSnapshotRef.current = snapshot;
    }
  }, []);

  // Full save with pixel data - only called on exit
  const saveFullProgress = useCallback(() => {
    if (!id) return;

    // Only save if the user actually painted something this session
    // This prevents overwriting completed levels when just viewing them
    if (!hasPaintedRef.current) return;

    const currentProgress = useGameStore.getState().progress;
    const complete = currentProgress >= 98;

    // Try to get fresh data from canvas, fall back to cached refs
    let paintedPixels: Set<number>;
    let snapshot: string | null;

    if (canvasRef.current) {
      paintedPixels = canvasRef.current.getPaintedPixels();
      snapshot = canvasRef.current.getCanvasSnapshot();
      if (snapshot) {
        latestSnapshotRef.current = snapshot;
      }
    } else {
      // Canvas already unmounted, use cached data
      paintedPixels = latestPaintedPixelsRef.current;
      snapshot = latestSnapshotRef.current;
    }

    saveFullState(id, currentProgress, complete, paintedPixels);
    lastSavedProgressRef.current = currentProgress;

    // Save preview image
    if (snapshot) {
      savePreview(id, snapshot);
    }
  }, [id, saveFullState]);

  // Save progress percentage when it changes (debounced, no pixels)
  // Also update cached snapshot for reliable unmount saving
  useEffect(() => {
    if (progress === lastSavedProgressRef.current || progress === 0) return;

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(() => {
      saveQuickProgress();
      // Update cached snapshot whenever we save progress
      updateCachedData();
    }, 500);

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [progress, saveQuickProgress, updateCachedData]);

  // Full save when app goes to background
  useEffect(() => {
    const handleAppStateChange = (nextAppState: AppStateStatus) => {
      if (nextAppState === 'background' || nextAppState === 'inactive') {
        saveFullProgress();
      }
    };

    const subscription = AppState.addEventListener('change', handleAppStateChange);
    return () => subscription.remove();
  }, [saveFullProgress]);

  // Full save on unmount (leaving screen)
  useEffect(() => {
    return () => {
      saveFullProgress();
    };
  }, [saveFullProgress]);

  // Handle victory - use local progress state to avoid stale global state issues
  useEffect(() => {
    if (progress >= 98 && !showVictory) {
      setShowVictory(true);
    }
  }, [progress, showVictory]);

  const handleProgressChange = useCallback((newProgress: number) => {
    // Mark that painting happened this session
    hasPaintedRef.current = true;
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
    // Clear cached snapshot and pixels
    latestSnapshotRef.current = null;
    latestPaintedPixelsRef.current = new Set();
    // Reset painting tracker since we're starting fresh
    hasPaintedRef.current = false;
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
