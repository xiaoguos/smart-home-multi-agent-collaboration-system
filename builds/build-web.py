import os
import subprocess

def build_web():
    subprocess.run(["pnpm", "build"], cwd="web")

if __name__ == "__main__":
    build_web()