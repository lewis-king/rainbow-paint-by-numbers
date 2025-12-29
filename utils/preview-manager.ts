import { Paths, File, Directory } from 'expo-file-system';

const PREVIEWS_DIR_NAME = 'previews';

function getPreviewsDir(): Directory {
  return new Directory(Paths.document, PREVIEWS_DIR_NAME);
}

function getPreviewFile(levelId: string): File {
  return new File(getPreviewsDir(), `${levelId}_preview.png`);
}

export function getPreviewPath(levelId: string): string {
  return getPreviewFile(levelId).uri;
}

export async function savePreview(levelId: string, base64Data: string): Promise<void> {
  try {
    const dir = getPreviewsDir();
    if (!dir.exists) {
      dir.create();
    }

    const file = getPreviewFile(levelId);
    // Convert base64 to Uint8Array and write
    const binaryString = atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    file.write(bytes);
  } catch (error) {
    console.warn('Failed to save preview:', error);
  }
}

export async function deletePreview(levelId: string): Promise<void> {
  try {
    const file = getPreviewFile(levelId);
    if (file.exists) {
      file.delete();
    }
  } catch (error) {
    console.warn('Failed to delete preview:', error);
  }
}

export async function previewExists(levelId: string): Promise<boolean> {
  try {
    const file = getPreviewFile(levelId);
    return file.exists;
  } catch {
    return false;
  }
}
