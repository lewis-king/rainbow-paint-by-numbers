# Rainbow Paint by Numbers

A wholesome paint-by-numbers app made with love, by a dad and daughter, for that daughter.


https://github.com/user-attachments/assets/452ce7af-f55c-423f-9a9c-9bdb2b1e5a4b


**Available on**
[Google Play](https://play.google.com/store/apps/details?id=king.meezy.rainbowpaintbynumbers)

## Why This Exists


Like many parents, I got tired of watching my daughter navigate through ad-riddled, in-app-purchase-laden colouring apps that seemed more interested in monetisation than providing a good experience. So we decided to make our own.

This app is tailored specifically to her taste, featuring cute designs that come to life when you complete a painting! The reward for finishing isn't a popup asking for money — it's watching your artwork animate into something magical.

## Asset Generation

All artwork and animations in this app are AI-generated and post-processed into paintable segments. The entire pipeline runs locally on an **NVIDIA RTX 5090** using [ComfyUI](https://github.com/comfyanonymous/ComfyUI).

Editable ComfyUI workflows, prompts, seeds, source artwork and visual quality
reviews live in [`image-processing/generation/`](image-processing/generation/README.md).
The generation tools support switching models independently of the game.

### Text-to-Image

The workflow generates clean, colourful base artwork from a subject prompt.

**Positive Prompt:**
```
(masterpiece), flat vector art, children's coloring book style, cute [SUBJECT], simple shapes, thick bold outlines, cel shaded, vibrant solid colors, white background, minimalist, high contrast, 2d game asset, no dithering
```![Uploading unnamed.webp…]()


**Negative Prompt:**
```
shading, gradients, noise, texture, realistic, photography, 3d, rendering, complex details, fuzzy, sketch, watermark, text, greyscale
```

This produces clean, bold, child-friendly artwork with distinct color regions perfect for a paint-by-numbers game.

### Image-to-Video

When a painting is completed, we play an animation that brings the static artwork to life. This gives kids that satisfying "wow" moment as their finished work starts moving!

### Post-Processing: Creating Paintable Segments

The generated images go through a post-processing pipeline to become usable game assets:

1. **Color Quantization** — Reduce the image to a limited palette of distinct, solid colors
2. **Boundary Detection** — Identify edges between color regions using contour detection
3. **Segment Extraction** — Convert each color region into a discrete, fillable polygon
4. **Outline Generation** — Create the thick black outlines that define each segment
5. **Metadata Export** — Map each segment to its target color for gameplay validation

The result is a set of clearly defined regions that players can tap to fill, with the app tracking progress toward the original colored design.

### Running the Post-Processing Script

Raw source files live in `image-processing/raw_assets/` and are named by level, for example `22.png` and optional `22.mp4`.

On a fresh clone, create the Python virtual environment and install the processing dependencies first:
```bash
cd image-processing
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

To process from a level number inclusive, run:
```bash
python process.py --from 22
```

That processes every numbered image from `22` upward. To process a bounded inclusive range:
```bash
python process.py --from 22 --to 28
```

Generated files are written to `image-processing/app_assets/{level}/`. Copy the finished level folders into `assets/images/levels/`, then add the static `require(...)` entries in `utils/level-loader.ts`.

## Tech Stack

Built with modern React Native tooling for a smooth, performant experience:

| Technology | Purpose |
|------------|---------|
| [React Native](https://reactnative.dev/) | Cross-platform mobile framework |
| [Expo](https://expo.dev/) | Development platform & tooling |
| [Shopify Skia](https://shopify.github.io/react-native-skia/) | High-performance 2D graphics rendering |
| [Zustand](https://zustand-demo.pmnd.rs/) | Lightweight state management |
| [React Native Reanimated](https://docs.swmansion.com/react-native-reanimated/) | Fluid animations |
| [React Native Gesture Handler](https://docs.swmansion.com/react-native-gesture-handler/) | Touch interactions (tap, pan, pinch-to-zoom) |
| [Expo Router](https://expo.github.io/router/) | File-based navigation |
| [Expo Video](https://docs.expo.dev/versions/latest/sdk/video/) | Victory animation playback |
| [Expo Haptics](https://docs.expo.dev/versions/latest/sdk/haptics/) | Tactile feedback on interactions |

## Getting Started

This app uses native modules (Skia, Reanimated, etc.) and requires a development build.

1. Install dependencies:
    ```bash
    npm install
    ```

2. Build and run on Android:
    ```bash
    npx expo run:android
    ```

    Or build and run on iOS:
    ```bash
    npx expo run:ios
    ```

## Deploying to Production

### For Development & Testing

Build and install to a connected Android device:
```bash
npx expo run:android
```

### For Production Release

1. Commit and push your code to GitHub:
    ```bash
    git add .
    git commit -m "Your changes"
    git push origin main
    ```

2. Build the Android App Bundle via EAS:
    ```bash
    npx eas build --platform android --profile production
    ```

3. Build the iOS app via EAS:
    ```bash
    npx eas build --platform ios --profile production
    ```

4. Download the `.aab` or `.ipa` file from the build output (saved to `~/Downloads/`) and verify it does not contain raw image-processing assets:
    ```bash
    npm run verify:dist -- ~/Downloads/your-build.aab
    npm run verify:dist -- ~/Downloads/your-build.ipa
    ```

5. Upload the verified Android App Bundle manually in Google Play Console.

6. Submit the verified iOS app to App Store Connect using EAS Submit:
    ```bash
    npx eas submit --platform ios --path ~/Downloads/your-build.ipa
    ```

    If you want EAS to prompt you to choose a recent build instead, you can run:
    ```bash
    npx eas submit --platform ios
    ```

**Note:** EAS Build pulls your code from GitHub, so make sure all changes are pushed before building.

## License

Made with love. Feel free to use this as inspiration for your own family projects.
