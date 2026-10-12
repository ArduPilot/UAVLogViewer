import { join } from "node:path";
import { tmpdir } from "node:os";
import glob from "glob";

// Log files for the parser tests: $TEST_LOG_DIR, else <tmp>/testlogs (filled by
// test/testlogfiles/logdownloader.sh), else test/testlogfiles
export function findTestLogs(extensions) {
    // match lower and upper case extensions (ArduPilot names logs *.BIN); glob's
    // nocase option does not work with absolute Windows paths
    const variants = extensions.flatMap((e) => [
        e.toLowerCase(),
        e.toUpperCase(),
    ]);
    const pattern = `*.{${variants.join(",")}}`;
    const dirs = [
        process.env.TEST_LOG_DIR,
        join(tmpdir(), "testlogs"),
        "test/testlogfiles",
    ].filter(Boolean);
    for (const dir of dirs) {
        const files = glob.sync(join(dir, pattern).replaceAll("\\", "/"));
        if (files.length > 0) {
            return files;
        }
    }
    return [];
}
