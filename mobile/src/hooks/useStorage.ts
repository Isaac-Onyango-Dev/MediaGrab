/**
 * MediaGrab Mobile - Storage Hook
 * Handles device storage checking and low space warnings.
 * Production v1.0.0 - No test/dev code.
 */

import { useState, useCallback } from 'react';
import * as FileSystem from 'expo-file-system';
import { Alert } from 'react-native';

export interface StorageInfo {
  totalBytes: number;
  freeBytes: number;
  totalGB: number;
  freeGB: number;
  freeMB: number;
  usagePercent: number;
  isLowSpace: boolean;
}

const LOW_SPACE_THRESHOLD_MB = 500;

/**
 * Hook for managing device storage awareness
 */
export function useStorage() {
  const [storageInfo, setStorageInfo] = useState<StorageInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Check available device storage
   */
  const checkStorage = useCallback(async (): Promise<StorageInfo | null> => {
    try {
      setIsLoading(true);
      
      const storageDir = FileSystem.documentDirectory;
      if (!storageDir) {
        console.warn('Storage directory not available');
        return null;
      }

      const freeDiskStorage = await FileSystem.getFreeDiskStorageAsync();
      const totalDiskStorage = await FileSystem.getTotalDiskCapacityAsync();

      const info: StorageInfo = {
        totalBytes: totalDiskStorage,
        freeBytes: freeDiskStorage,
        totalGB: totalDiskStorage / (1024 ** 3),
        freeGB: freeDiskStorage / (1024 ** 3),
        freeMB: freeDiskStorage / (1024 ** 2),
        usagePercent: ((totalDiskStorage - freeDiskStorage) / totalDiskStorage) * 100,
        isLowSpace: freeDiskStorage / (1024 ** 2) < LOW_SPACE_THRESHOLD_MB,
      };

      setStorageInfo(info);
      return info;
    } catch (error) {
      console.error('Failed to check storage:', error);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Warn user if storage is low
   * @param requiredMB - Estimated space needed for download
   * @returns true if user should proceed, false if cancelled
   */
  const warnIfLowSpace = useCallback(async (requiredMB?: number): Promise<boolean> => {
    const info = await checkStorage();
    
    if (!info) {
      // Can't check storage, allow download
      return true;
    }

    if (requiredMB && requiredMB > info.freeMB) {
      // Not enough space for this download
      Alert.alert(
        'Insufficient Storage',
        `This download requires approximately ${requiredMB.toFixed(0)}MB, but you only have ${info.freeMB.toFixed(0)}MB available.`,
        [{ text: 'OK' }]
      );
      return false;
    }

    if (info.isLowSpace) {
      // Low space warning
      return new Promise<boolean>((resolve) => {
        Alert.alert(
          'Low Storage Warning',
          `Your device has only ${info.freeMB.toFixed(0)}MB of storage remaining. Downloads may fail if space runs out.`,
          [
            { text: 'Cancel', style: 'cancel', onPress: () => resolve(false) },
            { text: 'Continue Anyway', onPress: () => resolve(true) },
          ]
        );
      });
    }

    return true;
  }, [checkStorage]);

  /**
   * Format bytes to human-readable string
   */
  const formatBytes = useCallback((bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
    return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
  }, []);

  return {
    storageInfo,
    isLoading,
    checkStorage,
    warnIfLowSpace,
    formatBytes,
  };
}
