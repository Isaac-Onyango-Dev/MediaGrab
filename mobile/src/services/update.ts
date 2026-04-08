/**
 * MediaGrab Mobile – Update Checker
 * Checks GitHub Releases for newer versions
 */

const REPO_URL = "https://api.github.com/repos/Isaac-Onyango-Dev/MediaGrab/releases/latest";

export interface UpdateInfo {
    version: string;
    downloadUrl: string;
    releaseNotes: string;
    apkUrl: string;
}

export async function checkForUpdate(currentVersion: string): Promise<UpdateInfo | null> {
    try {
        const resp = await fetch(REPO_URL, {
            headers: { "Accept": "application/vnd.github.v3+json" },
        });
        if (!resp.ok) return null;

        const release = await resp.json();
        const latest = release.tag_name.replace(/^v/, "");

        if (compareVersions(currentVersion, latest) >= 0) {
            return null;
        }

        const apkAsset = release.assets?.find((a: any) => a.name.endsWith(".apk"));
        return {
            version: latest,
            downloadUrl: apkAsset?.browser_download_url ?? release.html_url,
            releaseNotes: release.body ?? "No release notes available.",
            apkUrl: apkAsset?.browser_download_url ?? "",
        };
    } catch {
        return null;
    }
}

function compareVersions(a: string, b: string): number {
    const parse = (v: string) => v.split(".").map((x) => parseInt(x, 10) || 0);
    const [a1, a2, a3] = parse(a);
    const [b1, b2, b3] = parse(b);
    if (a1 !== b1) return a1 - b1;
    if (a2 !== b2) return a2 - b2;
    return (a3 || 0) - (b3 || 0);
}
