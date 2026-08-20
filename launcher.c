#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <libgen.h>
#include <mach-o/dyld.h>
#include <limits.h>

int main(int argc, char *argv[]) {
    char exe_path[PATH_MAX];
    uint32_t size = sizeof(exe_path);
    if (_NSGetExecutablePath(exe_path, &size) != 0) {
        fprintf(stderr, "Buffer too small for executable path\n");
        return 1;
    }

    // Resolve realpath
    char real_exe[PATH_MAX];
    if (!realpath(exe_path, real_exe)) {
        strncpy(real_exe, exe_path, sizeof(real_exe));
    }

    char *dir = dirname(real_exe); // Contents/MacOS
    char resources_dir[PATH_MAX];
    snprintf(resources_dir, sizeof(resources_dir), "%s/../Resources", dir);

    char script_path[PATH_MAX];
    snprintf(script_path, sizeof(script_path), "%s/macmic_gui.py", resources_dir);

    // Change working directory to Resources
    chdir(resources_dir);

    // Find best python3 on Apple Silicon
    const char *python_candidates[] = {
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/usr/bin/python3",
        "python3",
        NULL
    };

    const char *python_bin = NULL;
    for (int i = 0; python_candidates[i] != NULL; i++) {
        if (access(python_candidates[i], X_OK) == 0) {
            python_bin = python_candidates[i];
            break;
        }
    }
    if (!python_bin) {
        python_bin = "python3";
    }

    // Prepare arguments
    char **new_argv = malloc((argc + 3) * sizeof(char *));
    new_argv[0] = (char *)python_bin;
    new_argv[1] = script_path;
    for (int i = 1; i < argc; i++) {
        new_argv[i + 1] = argv[i];
    }
    new_argv[argc + 1] = NULL;

    // Exec python3
    execv(python_bin, new_argv);

    // Fallback to execvp
    execvp(python_bin, new_argv);

    perror("Failed to launch MacMic");
    return 1;
}
