#!/bin/bash
# Build all Dumont Cloud model images
#
# Usage:
#   ./build.sh          # Build all images
#   ./build.sh whisper  # Build only whisper
#   ./build.sh --push   # Build and push all to Docker Hub

set -e

cd "$(dirname "$0")"

REGISTRY="dumontcloud"
PUSH=false

# Check for --push flag
if [[ "$1" == "--push" ]]; then
    PUSH=true
    shift
fi

# Define all images
declare -A IMAGES=(
    ["whisper"]="whisper:4.40-cuda12.1"
    ["vllm"]="vllm:0.6.2-cuda12.1"
    ["diffusers"]="diffusers:0.28-cuda12.1"
    ["embeddings"]="embeddings:2.7-cuda12.1"
    ["vision"]="vision:4.40-cuda12.1"
    ["video"]="video:0.28-cuda12.1"
)

build_image() {
    local name=$1
    local tag=${IMAGES[$name]}
    local full_tag="$REGISTRY/$tag"

    echo "=========================================="
    echo "Building: $full_tag"
    echo "=========================================="

    docker build -f "Dockerfile.$name" -t "$full_tag" .

    if [ "$PUSH" = true ]; then
        echo "Pushing: $full_tag"
        docker push "$full_tag"
    fi

    echo "✓ $full_tag built successfully"
}

# Build specified image or all
if [ -n "$1" ]; then
    if [ -z "${IMAGES[$1]}" ]; then
        echo "Unknown image: $1"
        echo "Available: ${!IMAGES[@]}"
        exit 1
    fi
    build_image "$1"
else
    for name in "${!IMAGES[@]}"; do
        build_image "$name"
    done
fi

echo ""
echo "=========================================="
echo "Build complete!"
if [ "$PUSH" = true ]; then
    echo "Images pushed to Docker Hub: $REGISTRY/"
else
    echo "Run with --push to push to Docker Hub"
fi
echo "=========================================="
