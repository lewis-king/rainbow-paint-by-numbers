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
  // PaintStyle removed since we don't need strokes anymore
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
const UNPAINTED_COLOR = { r: 230, g: 230, b: 240 }; 

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

const fontFamily = Platform.select({ ios: 'Helvetica', default: 'sans-serif' });
const fontStyle = {
  fontFamily,
  fontSize: 10, 
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

  const zoomScale = useSharedValue(1);
  const translateX = useSharedValue(0);
  const translateY = useSharedValue(0);
  const savedScale = useSharedValue(1);
  const savedTranslateX = useSharedValue(0);
  const savedTranslateY = useSharedValue(0);

  // REMOVED: textStrokePaint logic is gone.

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

  const userCanvasDataRef = useRef<Uint8Array | null>(null);
  const [userCanvasImage, setUserCanvasImage] = useState<SkImage | null>(null);
  const pendingImageUpdateRef = useRef<boolean>(false);
  const imageUpdateTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastUpdateTimeRef = useRef<number>(0);
  const MIN_UPDATE_INTERVAL = 150; 

  const [pendingStrokes, setPendingStrokes] = useState<Array<{x: number, y: number, color: string, radius: number}>>([]);
  const pendingStrokesCountRef = useRef(0);

  const mapPixelDataRef = useRef<Uint8Array | null>(null);
  const [mapReady, setMapReady] = useState(false);

  const paintedPixelsRef = useRef<Set<number>>(new Set());
  const totalPaintablePixelsRef = useRef<number>(0);
  
  const hasRestoredRef = useRef(false);

  const imgWidth = levelData.dimensions.w;
  const imgHeight = levelData.dimensions.h;

  useImperativeHandle(ref, () => ({
    getPaintedPixels: () => {
      // If user has painted this session, return current pixels
      if (paintedPixelsRef.current.size > 0) {
        return paintedPixelsRef.current;
      }

      // If no painting happened but we have saved data, preserve it
      if (initialPaintedPixels && initialPaintedPixels.length > 0) {
        return new Set(initialPaintedPixels);
      }

      // No pixels to return
      return new Set();
    },
    getCanvasSnapshot: () => {
      if (!userCanvasImage || !linesImage) return null;
      try {
        const surface = Skia.Surface.Make(imgWidth, imgHeight);
        if (!surface) return null;
        const canvas = surface.getCanvas();
        canvas.drawImage(userCanvasImage, 0, 0);
        canvas.drawImage(linesImage, 0, 0);
        const compositeImage = surface.makeImageSnapshot();
        const result = compositeImage.encodeToBase64(ImageFormat.PNG);
        compositeImage.dispose();
        surface.dispose();
        return result;
      } catch (error) {
        console.warn('Failed to encode canvas snapshot:', error);
        return null;
      }
    },
  }), [userCanvasImage, linesImage, imgWidth, imgHeight, initialPaintedPixels]);

  const createCanvasImage = useCallback((data: Uint8Array, immediate = false) => {
    const now = Date.now();

    const doUpdate = () => {
      try {
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
            if (prevImage) {
              try { prevImage.dispose(); } catch {}
            }
            return image;
          });
        }
        lastUpdateTimeRef.current = Date.now();
        pendingImageUpdateRef.current = false;
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
      if (pendingImageUpdateRef.current) return;
      const timeSinceLastUpdate = now - lastUpdateTimeRef.current;
      const delay = Math.max(0, MIN_UPDATE_INTERVAL - timeSinceLastUpdate);
      pendingImageUpdateRef.current = true;
      imageUpdateTimeoutRef.current = setTimeout(doUpdate, delay);
    }
  }, [imgWidth, imgHeight]);

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

    hasRestoredRef.current = false;

    createCanvasImage(data, true);
  }, [imgWidth, imgHeight, createCanvasImage]);

  useEffect(() => {
    if (!mapImage) return;
    try {
      const pixels = mapImage.readPixels(0, 0, {
        width: imgWidth,
        height: imgHeight,
        colorType: ColorType.RGBA_8888,
        alphaType: AlphaType.Unpremul,
      });

      if (pixels) {
        const pixelData = pixels instanceof Uint8Array ? pixels : new Uint8Array(pixels.buffer);
        mapPixelDataRef.current = pixelData;

        let paintableCount = 0;
        for (let i = 0; i < pixelData.length; i += 4) {
          if (pixelData[i] !== 255 && pixelData[i] !== 254) {
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

  useEffect(() => {
    if (!mapReady || !userCanvasDataRef.current || !mapPixelDataRef.current) return;
    if (!initialPaintedPixels || initialPaintedPixels.length === 0) return;

    const userCanvasData = userCanvasDataRef.current;
    const mapPixelData = mapPixelDataRef.current;
    const palette = levelData.palette;

    // Clear and rebuild - makes this effect idempotent
    paintedPixelsRef.current = new Set();

    // First, reset canvas to unpainted state
    for (let i = 0; i < userCanvasData.length; i += 4) {
      userCanvasData[i] = UNPAINTED_COLOR.r;
      userCanvasData[i + 1] = UNPAINTED_COLOR.g;
      userCanvasData[i + 2] = UNPAINTED_COLOR.b;
      userCanvasData[i + 3] = 255;
    }

    // Then restore saved pixels
    for (const pixelKey of initialPaintedPixels) {
      const mapIdx = pixelKey * 4;
      const colorIdx = mapPixelData[mapIdx];

      if (colorIdx === 255 || colorIdx === 254 || colorIdx < 0 || colorIdx >= palette.length) continue;

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

    if (totalPaintablePixelsRef.current > 0) {
      const progress = (paintedPixelsRef.current.size / totalPaintablePixelsRef.current) * 100;
      onProgressChange(progress);
    }
  }, [mapReady, initialPaintedPixels, levelData.palette, createCanvasImage, onProgressChange]);

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

  const paintBrush = useCallback((
    canvasX: number,
    canvasY: number,
    isMagicBrush: boolean
  ) => {
    const userCanvasData = userCanvasDataRef.current;
    const mapPixelData = mapPixelDataRef.current;
    if (!userCanvasData || !mapPixelData || !mapReady) return;

    const currentScale = zoomScale.value;
    const currentTranslateX = translateX.value;
    const currentTranslateY = translateY.value;

    const centerX = canvasWidth / 2;
    const centerY = canvasHeight / 2;
    const adjustedX = (canvasX - currentTranslateX - centerX) / currentScale + centerX;
    const adjustedY = (canvasY - currentTranslateY - centerY) / currentScale + centerY;

    const imgX = Math.floor(adjustedX / scale);
    const imgY = Math.floor(adjustedY / scale);

    const radius = BRUSH_SIZES[brushSize];
    let painted = false;

    const currentSelectedColorIndex = useGameStore.getState().selectedColorIndex;
    const palette = levelData.palette;

    for (let dy = -radius; dy <= radius; dy++) {
      for (let dx = -radius; dx <= radius; dx++) {
        if (dx * dx + dy * dy > radius * radius) continue;

        const px = imgX + dx;
        const py = imgY + dy;

        if (px < 0 || px >= imgWidth || py < 0 || py >= imgHeight) continue;

        const mapIdx = (py * imgWidth + px) * 4;
        const mapColorIdx = mapPixelData[mapIdx];

        if (mapColorIdx === 255 || mapColorIdx === 254 || mapColorIdx < 0 || mapColorIdx >= palette.length) continue;

        const dataIdx = (py * imgWidth + px) * 4;
        const pixelKey = py * imgWidth + px;

        let color: [number, number, number];
        if (isMagicBrush) {
          if (mapColorIdx !== currentSelectedColorIndex) continue;
          color = hexToRgb(palette[currentSelectedColorIndex]);
        } else {
          color = hexToRgb(palette[mapColorIdx]);
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
      const centerMapIdx = (imgY * imgWidth + imgX) * 4;
      const centerColorIdx = mapPixelData[centerMapIdx];

      const needsFlush = pendingStrokesCountRef.current >= 50;
      if (needsFlush) {
        createCanvasImage(userCanvasData, true);
      }

      if (centerColorIdx !== 255 && centerColorIdx !== 254 && centerColorIdx >= 0 && centerColorIdx < palette.length) {
        const strokeColor = isMagicBrush ? palette[currentSelectedColorIndex] : palette[centerColorIdx];
        const newStroke = { x: adjustedX, y: adjustedY, color: strokeColor, radius: radius * scale };

        if (needsFlush) {
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
  }, [mapReady, scale, brushSize, levelData.palette, hexToRgb, createCanvasImage, updateProgress, imgWidth, imgHeight, canvasWidth, canvasHeight, zoomScale, translateX, translateY]);

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

    const centerX = canvasWidth / 2;
    const centerY = canvasHeight / 2;
    const adjustedX = (canvasX - currentTranslateX - centerX) / currentScale + centerX;
    const adjustedY = (canvasY - currentTranslateY - centerY) / currentScale + centerY;

    const startX = Math.floor(adjustedX / scale);
    const startY = Math.floor(adjustedY / scale);

    if (startX < 0 || startX >= imgWidth || startY < 0 || startY >= imgHeight) return;

    const startMapIdx = (startY * imgWidth + startX) * 4;
    const targetColorIndex = mapPixelData[startMapIdx];

    if (targetColorIndex === 255 || targetColorIndex === 254) return;

    const currentSelectedColorIndex = useGameStore.getState().selectedColorIndex;

    if (targetColorIndex !== currentSelectedColorIndex) {
      return;
    }

    const fillColor = hexToRgb(levelData.palette[currentSelectedColorIndex]);

    const stack: number[] = [startX, startY];
    const visited = new Set<number>();
    let iterations = 0;
    
    // Increased Iteration Limit for High Res
    const maxIterationsPerFrame = imgWidth * imgHeight; 

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

      stack.push(
        x + 1, y,     
        x - 1, y,     
        x, y + 1,     
        x, y - 1,     
        x + 1, y + 1, 
        x - 1, y + 1, 
        x + 1, y - 1, 
        x - 1, y - 1  
      );
      iterations++;
    }

    createCanvasImage(userCanvasData, true); 
    updateProgress();
  }, [mapReady, scale, levelData.palette, hexToRgb, createCanvasImage, updateProgress, imgWidth, imgHeight, canvasWidth, canvasHeight, zoomScale, translateX, translateY]);

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
            <Image
              image={userCanvasImage}
              x={0}
              y={0}
              width={canvasWidth}
              height={canvasHeight}
              fit="fill"
            />
            {pendingStrokes.map((stroke, i) => (
              <Circle
                key={`stroke-${i}`}
                cx={stroke.x}
                cy={stroke.y}
                r={stroke.radius}
                color={stroke.color}
              />
            ))}
            <Image
              image={linesImage}
              x={0}
              y={0}
              width={canvasWidth}
              height={canvasHeight}
              fit="fill"
            />
            {/* UPDATED: Only rendering the single text element now */}
            <Group>
              {scaledNumbers.map((n, i) => (
                <Text
                  key={`${n.x}-${n.y}-${i}`}
                  x={n.displayX - 4}
                  y={n.displayY + 3}
                  text={String(n.number)}
                  font={font}
                  color="#666666" 
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