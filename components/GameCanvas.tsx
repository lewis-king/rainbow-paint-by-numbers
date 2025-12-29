import React, { useCallback, useEffect, useMemo, useRef, useState, useImperativeHandle, forwardRef } from 'react';
import { View, StyleSheet, Dimensions, Platform } from 'react-native';
import {
  Canvas,
  Image,
  useImage,
  Skia,
  SkImage,
  Text,
  matchFont,
  ColorType,
  AlphaType,
  Group,
  Circle,
  ImageFormat,
} from '@shopify/react-native-skia';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  runOnJS,
} from 'react-native-reanimated';
import type { LevelData } from '@/types/level';
import { useGameStore, BRUSH_SIZES } from '@/store/game-store';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// Tinted background color so white painted areas are visible
const UNPAINTED_COLOR = { r: 230, g: 230, b: 240 }; // Light lavender tint

interface GameCanvasProps {
  levelData: LevelData;
  linesUri: string;
  mapUri: string;
  onProgressChange: (progress: number) => void;
  initialPaintedPixels?: number[];
}

export interface GameCanvasHandle {
  getPaintedPixels: () => Set<number>;
  getCanvasSnapshot: () => string | null;
}

// Smaller font for number labels
const fontFamily = Platform.select({ ios: 'Helvetica', default: 'sans-serif' });
const fontStyle = {
  fontFamily,
  fontSize: 12,
  fontWeight: 'bold' as const,
};

export const GameCanvas = forwardRef<GameCanvasHandle, GameCanvasProps>(function GameCanvas(
  { levelData, linesUri, mapUri, onProgressChange, initialPaintedPixels },
  ref
) {
  const linesImage = useImage(linesUri);
  const mapImage = useImage(mapUri);
  const font = matchFont(fontStyle);

  const { brushSize } = useGameStore();

  // Zoom and pan state
  const zoomScale = useSharedValue(1);
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const savedScale = useSharedValue(1);
  const savedTranslateX = useSharedValue(0);
  const savedTranslateY = useSharedValue(0);

  // Calculate canvas dimensions to fit screen while maintaining aspect ratio
  const { canvasWidth, canvasHeight, scale } = useMemo(() => {
    const imgWidth = levelData.dimensions.w;
    const imgHeight = levelData.dimensions.h;
    const maxWidth = SCREEN_WIDTH - 16;
    const maxHeight = SCREEN_HEIGHT - 280;

    const scaleX = maxWidth / imgWidth;
    const scaleY = maxHeight / imgHeight;
    const s = Math.min(scaleX, scaleY);

    return {
      canvasWidth: imgWidth * s,
      canvasHeight: imgHeight * s,
      scale: s,
    };
  }, [levelData.dimensions]);

  // User canvas pixel data (white initially)
  const userCanvasDataRef = useRef<Uint8Array | null>(null);
  const [userCanvasImage, setUserCanvasImage] = useState<SkImage | null>(null);
  const pendingImageUpdateRef = useRef<boolean>(false);
  const imageUpdateTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastUpdateTimeRef = useRef<number>(0);
  const MIN_UPDATE_INTERVAL = 150; // Minimum ms between image updates

  // Pending brush strokes for immediate visual feedback
  const [pendingStrokes, setPendingStrokes] = useState<Array<{x: number, y: number, color: string, radius: number}>>([]);
  const pendingStrokesCountRef = useRef(0);

  // Map pixel data for reading color indices
  const mapPixelDataRef = useRef<Uint8Array | null>(null);
  const [mapReady, setMapReady] = useState(false);

  // Painted pixels tracking
  const paintedPixelsRef = useRef<Set<number>>(new Set());
  const totalPaintablePixelsRef = useRef<number>(0);
  const hasRestoredRef = useRef(false);

  const imgWidth = levelData.dimensions.w;
  const imgHeight = levelData.dimensions.h;

  // Expose painted pixels and snapshot to parent
  useImperativeHandle(ref, () => ({
    getPaintedPixels: () => paintedPixelsRef.current,
    getCanvasSnapshot: () => {
      if (!userCanvasImage) return null;
      try {
        return userCanvasImage.encodeToBase64(ImageFormat.PNG);
      } catch (error) {
        console.warn('Failed to encode canvas snapshot:', error);
        return null;
      }
    },
  }), [userCanvasImage]);

  // Throttled image creation to prevent memory issues
  const createCanvasImage = useCallback((data: Uint8Array, immediate = false) => {
    const now = Date.now();

    const doUpdate = () => {
      try {
        // Copy data to avoid issues with mutating array
        const dataCopy = new Uint8Array(data);
        const skData = Skia.Data.fromBytes(dataCopy);
        const image = Skia.Image.MakeImage(
          {
            width: imgWidth,
            height: imgHeight,
            colorType: ColorType.RGBA_8888,
            alphaType: AlphaType.Unpremul,
          },
          skData,
          imgWidth * 4
        );
        if (image) {
          setUserCanvasImage((prevImage) => {
            // Dispose previous image to free memory
            if (prevImage) {
              try {
                prevImage.dispose();
              } catch {
                // Ignore disposal errors
              }
            }
            return image;
          });
        }
        lastUpdateTimeRef.current = Date.now();
        pendingImageUpdateRef.current = false;
        // Clear pending strokes since they're now in the image
        setPendingStrokes([]);
        pendingStrokesCountRef.current = 0;
      } catch (error) {
        console.warn('Failed to create canvas image:', error);
        pendingImageUpdateRef.current = false;
      }
    };

    if (immediate) {
      if (imageUpdateTimeoutRef.current) {
        clearTimeout(imageUpdateTimeoutRef.current);
        imageUpdateTimeoutRef.current = null;
      }
      doUpdate();
    } else {
      // Skip if update is already pending
      if (pendingImageUpdateRef.current) return;

      // Calculate delay based on last update time
      const timeSinceLastUpdate = now - lastUpdateTimeRef.current;
      const delay = Math.max(0, MIN_UPDATE_INTERVAL - timeSinceLastUpdate);

      pendingImageUpdateRef.current = true;
      imageUpdateTimeoutRef.current = setTimeout(doUpdate, delay);
    }
  }, [imgWidth, imgHeight]);

  // Initialize user canvas with tinted background
  useEffect(() => {
    const pixelCount = imgWidth * imgHeight * 4;
    const data = new Uint8Array(pixelCount);
    for (let i = 0; i < pixelCount; i += 4) {
      data[i] = UNPAINTED_COLOR.r;
      data[i + 1] = UNPAINTED_COLOR.g;
      data[i + 2] = UNPAINTED_COLOR.b;
      data[i + 3] = 255;
    }
    userCanvasDataRef.current = data;
    paintedPixelsRef.current = new Set();
    createCanvasImage(data, true); // immediate update for initial render
  }, [imgWidth, imgHeight, createCanvasImage]);

  // Extract map pixel data when map image loads
  useEffect(() => {
    if (!mapImage) return;

    try {
      // Read pixels directly from the image
      const pixels = mapImage.readPixels(0, 0, {
        width: imgWidth,
        height: imgHeight,
        colorType: ColorType.RGBA_8888,
        alphaType: AlphaType.Unpremul,
      });

      if (pixels) {
        const pixelData = pixels instanceof Uint8Array ? pixels : new Uint8Array(pixels.buffer);
        mapPixelDataRef.current = pixelData;

        // Count only paintable pixels (where map value is NOT 255)
        // 255 = background/outside boundary that doesn't need painting
        let paintableCount = 0;
        for (let i = 0; i < pixelData.length; i += 4) {
          if (pixelData[i] !== 255) {
            paintableCount++;
          }
        }
        totalPaintablePixelsRef.current = paintableCount;
        setMapReady(true);
      }
    } catch (error) {
      console.warn('Failed to read map pixels:', error);
    }
  }, [mapImage, imgWidth, imgHeight]);

  // Restore canvas from saved painted pixels
  useEffect(() => {
    if (!mapReady || !initialPaintedPixels || hasRestoredRef.current) return;
    if (!userCanvasDataRef.current || !mapPixelDataRef.current) return;

    const userCanvasData = userCanvasDataRef.current;
    const mapPixelData = mapPixelDataRef.current;
    const palette = levelData.palette;

    // Restore each painted pixel
    for (const pixelKey of initialPaintedPixels) {
      const mapIdx = pixelKey * 4;
      const colorIdx = mapPixelData[mapIdx];

      // Skip invalid pixels
      if (colorIdx === 255 || colorIdx < 0 || colorIdx >= palette.length) continue;

      const hex = palette[colorIdx];
      const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
      if (!result) continue;

      const r = parseInt(result[1], 16);
      const g = parseInt(result[2], 16);
      const b = parseInt(result[3], 16);

      const dataIdx = pixelKey * 4;
      userCanvasData[dataIdx] = r;
      userCanvasData[dataIdx + 1] = g;
      userCanvasData[dataIdx + 2] = b;
      userCanvasData[dataIdx + 3] = 255;

      paintedPixelsRef.current.add(pixelKey);
    }

    hasRestoredRef.current = true;
    createCanvasImage(userCanvasData, true);

    // Update progress after restoration
    if (totalPaintablePixelsRef.current > 0) {
      const progress = (paintedPixelsRef.current.size / totalPaintablePixelsRef.current) * 100;
      onProgressChange(progress);
    }
  }, [mapReady, initialPaintedPixels, levelData.palette, createCanvasImage, onProgressChange]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (imageUpdateTimeoutRef.current) {
        clearTimeout(imageUpdateTimeoutRef.current);
      }
    };
  }, []);

  const hexToRgb = useCallback((hex: string): [number, number, number] => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!result) return [0, 0, 0];
    return [
      parseInt(result[1], 16),
      parseInt(result[2], 16),
      parseInt(result[3], 16),
    ];
  }, []);

  const updateProgress = useCallback(() => {
    if (totalPaintablePixelsRef.current === 0) return;
    const progress = (paintedPixelsRef.current.size / totalPaintablePixelsRef.current) * 100;
    onProgressChange(progress);
  }, [onProgressChange]);

  // Optimized brush painting using refs
  const paintBrush = useCallback((
    canvasX: number,
    canvasY: number,
    isMagicBrush: boolean
  ) => {
    const userCanvasData = userCanvasDataRef.current;
    const mapPixelData = mapPixelDataRef.current;
    if (!userCanvasData || !mapPixelData || !mapReady) return;

    // Account for zoom and pan
    const currentScale = zoomScale.value;
    const currentTranslateX = translateX.value;
    const currentTranslateY = translateY.value;

    // Convert screen coordinates to canvas coordinates
    const adjustedX = (canvasX - currentTranslateX) / currentScale;
    const adjustedY = (canvasY - currentTranslateY) / currentScale;

    const imgX = Math.floor(adjustedX / scale);
    const imgY = Math.floor(adjustedY / scale);

    const radius = BRUSH_SIZES[brushSize];
    let painted = false;

    const currentSelectedColorIndex = useGameStore.getState().selectedColorIndex;
    const palette = levelData.palette;

    // For immediate visual feedback - collect stroke info
    const newStrokes: Array<{x: number, y: number, color: string, radius: number}> = [];

    for (let dy = -radius; dy <= radius; dy++) {
      for (let dx = -radius; dx <= radius; dx++) {
        if (dx * dx + dy * dy > radius * radius) continue;

        const px = imgX + dx;
        const py = imgY + dy;

        if (px < 0 || px >= imgWidth || py < 0 || py >= imgHeight) continue;

        const mapIdx = (py * imgWidth + px) * 4;
        const mapColorIdx = mapPixelData[mapIdx];

        // Skip background pixels (255) and invalid indices
        if (mapColorIdx === 255 || mapColorIdx < 0 || mapColorIdx >= palette.length) continue;

        const dataIdx = (py * imgWidth + px) * 4;
        const pixelKey = py * imgWidth + px;

        let color: [number, number, number];
        let hexColor: string;
        if (isMagicBrush) {
          if (mapColorIdx !== currentSelectedColorIndex) continue;
          color = hexToRgb(palette[currentSelectedColorIndex]);
          hexColor = palette[currentSelectedColorIndex];
        } else {
          color = hexToRgb(palette[mapColorIdx]);
          hexColor = palette[mapColorIdx];
        }

        if (userCanvasData[dataIdx] !== color[0] ||
            userCanvasData[dataIdx + 1] !== color[1] ||
            userCanvasData[dataIdx + 2] !== color[2]) {
          userCanvasData[dataIdx] = color[0];
          userCanvasData[dataIdx + 1] = color[1];
          userCanvasData[dataIdx + 2] = color[2];
          userCanvasData[dataIdx + 3] = 255;

          if (!paintedPixelsRef.current.has(pixelKey)) {
            paintedPixelsRef.current.add(pixelKey);
          }
          painted = true;
        }
      }
    }

    if (painted) {
      // Add immediate visual feedback stroke at brush center
      const centerMapIdx = (imgY * imgWidth + imgX) * 4;
      const centerColorIdx = mapPixelData[centerMapIdx];

      // Check if we need to flush before adding more strokes
      const needsFlush = pendingStrokesCountRef.current >= 50;
      if (needsFlush) {
        // Force immediate update to bake current strokes into image
        createCanvasImage(userCanvasData, true);
      }

      if (centerColorIdx !== 255 && centerColorIdx >= 0 && centerColorIdx < palette.length) {
        const strokeColor = isMagicBrush ? palette[currentSelectedColorIndex] : palette[centerColorIdx];
        const newStroke = { x: adjustedX, y: adjustedY, color: strokeColor, radius: radius * scale };

        if (needsFlush) {
          // After flush, start fresh with just this stroke
          setPendingStrokes([newStroke]);
          pendingStrokesCountRef.current = 1;
        } else {
          setPendingStrokes(prev => [...prev, newStroke]);
          pendingStrokesCountRef.current++;
        }
      }

      if (!needsFlush) {
        createCanvasImage(userCanvasData);
      }
      updateProgress();
    }
  }, [mapReady, scale, brushSize, levelData.palette, hexToRgb, createCanvasImage, updateProgress, imgWidth, imgHeight, zoomScale, translateX, translateY]);

  // Flood fill for bucket tool
  const floodFill = useCallback((
    canvasX: number,
    canvasY: number
  ) => {
    const userCanvasData = userCanvasDataRef.current;
    const mapPixelData = mapPixelDataRef.current;
    if (!userCanvasData || !mapPixelData || !mapReady) return;

    const currentScale = zoomScale.value;
    const currentTranslateX = translateX.value;
    const currentTranslateY = translateY.value;

    const adjustedX = (canvasX - currentTranslateX) / currentScale;
    const adjustedY = (canvasY - currentTranslateY) / currentScale;

    const startX = Math.floor(adjustedX / scale);
    const startY = Math.floor(adjustedY / scale);

    if (startX < 0 || startX >= imgWidth || startY < 0 || startY >= imgHeight) return;

    const startMapIdx = (startY * imgWidth + startX) * 4;
    const targetColorIndex = mapPixelData[startMapIdx];

    // Don't fill background pixels (255)
    if (targetColorIndex === 255) return;

    const currentSelectedColorIndex = useGameStore.getState().selectedColorIndex;

    if (targetColorIndex !== currentSelectedColorIndex) {
      // Wrong color - could play sound here
      return;
    }

    const fillColor = hexToRgb(levelData.palette[currentSelectedColorIndex]);

    // Use iterative flood fill with chunking to avoid blocking
    const stack: number[] = [startX, startY];
    const visited = new Set<number>();
    let iterations = 0;
    const maxIterationsPerFrame = 50000; // Increased for 8-connectivity

    while (stack.length > 0 && iterations < maxIterationsPerFrame) {
      const y = stack.pop()!;
      const x = stack.pop()!;
      const key = y * imgWidth + x;

      if (visited.has(key)) continue;
      if (x < 0 || x >= imgWidth || y < 0 || y >= imgHeight) continue;

      const mapIdx = (y * imgWidth + x) * 4;
      if (mapPixelData[mapIdx] !== targetColorIndex) continue;

      visited.add(key);

      const dataIdx = (y * imgWidth + x) * 4;
      userCanvasData[dataIdx] = fillColor[0];
      userCanvasData[dataIdx + 1] = fillColor[1];
      userCanvasData[dataIdx + 2] = fillColor[2];
      userCanvasData[dataIdx + 3] = 255;

      if (!paintedPixelsRef.current.has(key)) {
        paintedPixelsRef.current.add(key);
      }

      // 8-connectivity: include diagonals to match preprocessing script
      stack.push(
        x + 1, y,     // right
        x - 1, y,     // left
        x, y + 1,     // down
        x, y - 1,     // up
        x + 1, y + 1, // diagonal: bottom-right
        x - 1, y + 1, // diagonal: bottom-left
        x + 1, y - 1, // diagonal: top-right
        x - 1, y - 1  // diagonal: top-left
      );
      iterations++;
    }

    createCanvasImage(userCanvasData, true); // immediate for bucket fill
    updateProgress();
  }, [mapReady, scale, levelData.palette, hexToRgb, createCanvasImage, updateProgress, imgWidth, imgHeight, zoomScale, translateX, translateY]);

  // Wrapper functions for runOnJS
  const handlePan = useCallback((x: number, y: number) => {
    const tool = useGameStore.getState().selectedTool;
    if (tool === 'brush') {
      paintBrush(x, y, true);
    } else if (tool === 'rainbow') {
      paintBrush(x, y, false);
    }
  }, [paintBrush]);

  const handleTap = useCallback((x: number, y: number) => {
    const tool = useGameStore.getState().selectedTool;
    if (tool === 'bucket') {
      floodFill(x, y);
    } else if (tool === 'brush') {
      paintBrush(x, y, true);
    } else if (tool === 'rainbow') {
      paintBrush(x, y, false);
    }
  }, [paintBrush, floodFill]);

  // Gesture handlers
  const panGesture = Gesture.Pan()
    .minPointers(1)
    .maxPointers(1)
    .onUpdate((e) => {
      runOnJS(handlePan)(e.x, e.y);
    });

  const tapGesture = Gesture.Tap()
    .onEnd((e) => {
      runOnJS(handleTap)(e.x, e.y);
    });

  const pinchGesture = Gesture.Pinch()
    .onStart(() => {
      savedScale.value = zoomScale.value;
    })
    .onUpdate((e) => {
      const newScale = savedScale.value * e.scale;
      zoomScale.value = Math.min(Math.max(newScale, 0.5), 4);
    })
    .onEnd(() => {
      if (zoomScale.value < 1) {
        zoomScale.value = withSpring(1);
        translateX.value = withSpring(0);
        translateY.value = withSpring(0);
      }
    });

  const dragGesture = Gesture.Pan()
    .minPointers(2)
    .onStart(() => {
      savedTranslateX.value = translateX.value;
      savedTranslateY.value = translateY.value;
    })
    .onUpdate((e) => {
      if (zoomScale.value > 1) {
        translateX.value = savedTranslateX.value + e.translationX;
        translateY.value = savedTranslateY.value + e.translationY;
      }
    });

  const composedGesture = Gesture.Simultaneous(
    pinchGesture,
    dragGesture,
    Gesture.Exclusive(panGesture, tapGesture)
  );

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [
      { translateX: translateX.value },
      { translateY: translateY.value },
      { scale: zoomScale.value },
    ],
  }));

  // Scale numbers for display
  const scaledNumbers = useMemo(() => {
    return levelData.numbers.map((n) => ({
      ...n,
      displayX: n.x * scale,
      displayY: n.y * scale,
    }));
  }, [levelData.numbers, scale]);

  if (!linesImage || !userCanvasImage) {
    return <View style={[styles.container, { width: canvasWidth, height: canvasHeight }]} />;
  }

  return (
    <GestureDetector gesture={composedGesture}>
      <View style={styles.wrapper}>
        <Animated.View style={[styles.canvasWrapper, animatedStyle]}>
          <Canvas style={{ width: canvasWidth, height: canvasHeight }}>
            {/* Layer 1: User painted canvas */}
            <Image
              image={userCanvasImage}
              x={0}
              y={0}
              width={canvasWidth}
              height={canvasHeight}
              fit="fill"
            />

            {/* Layer 2: Pending strokes for immediate visual feedback */}
            {pendingStrokes.map((stroke, i) => (
              <Circle
                key={`stroke-${i}`}
                cx={stroke.x}
                cy={stroke.y}
                r={stroke.radius}
                color={stroke.color}
              />
            ))}

            {/* Layer 3: Lines overlay */}
            <Image
              image={linesImage}
              x={0}
              y={0}
              width={canvasWidth}
              height={canvasHeight}
              fit="fill"
            />

            {/* Layer 4: Number labels */}
            <Group>
              {scaledNumbers.map((n, i) => (
                <Text
                  key={`${n.x}-${n.y}-${i}`}
                  x={n.displayX - 5}
                  y={n.displayY + 4}
                  text={String(n.number)}
                  font={font}
                  color="#444444"
                />
              ))}
            </Group>
          </Canvas>
        </Animated.View>
      </View>
    </GestureDetector>
  );
});

const styles = StyleSheet.create({
  wrapper: {
    overflow: 'hidden',
    borderRadius: 12,
    backgroundColor: '#fff',
  },
  canvasWrapper: {
    backgroundColor: '#fff',
  },
  container: {
    backgroundColor: '#fff',
    borderRadius: 12,
    overflow: 'hidden',
  },
});
