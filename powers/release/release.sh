#!/usr/bin/env bash

set -euo pipefail

# Generic release script for any project.
#
# Supports version bumping in:
#   - package.json (Node/pnpm/npm projects)
#   - */package.json (monorepo workspaces)
#   - Go version constants (Version = "X.Y.Z" pattern)
#   - Cargo.toml (Rust projects)
#   - pyproject.toml (Python projects)
#
# Version files can be customized via .release.conf in the project root.

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find project root (nearest git root from cwd)
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

# Configuration
DRY_RUN=false
SKIP_CHECKS=false
NO_PUSH=false
VERSION=""
NOTES_FILE=""
VERSION_FILES=()

# Help message
usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] VERSION

Create a new release with automated version updates and GitHub release.

ARGUMENTS:
    VERSION     Version number in semver format (e.g., 0.0.1, 1.2.3, 2.0.0-beta.1)
                Can be prefixed with 'v' or not (both v0.0.1 and 0.0.1 are valid)

OPTIONS:
    -h, --help          Show this help message
    -d, --dry-run       Run without making any changes (validation only)
    -n, --no-push       Create tag locally but don't push (for testing)
    --notes-file FILE   Path to a file containing release notes (required for GitHub release)
    --skip-checks       Skip git status and branch checks (use with caution)

CONFIGURATION:
    Create a .release.conf file in your project root to customize behavior.
    The file is sourced as bash and can set:

        # Explicit list of files to version-bump (overrides auto-detection)
        VERSION_FILES=(
            "package.json"
            "apps/web/package.json"
            "src/version.go"
        )

    Without .release.conf, the script auto-detects version files.

EXAMPLES:
    $(basename "$0") 0.0.1 --notes-file notes.md    # Create release with notes
    $(basename "$0") v1.2.3 --notes-file notes.md    # Create release v1.2.3
    $(basename "$0") --dry-run 0.0.2                  # Test release process
    $(basename "$0") --no-push 0.0.1                  # Create tag locally only

PROCESS:
    1. Validate git repository state (clean working directory)
    2. Validate version format (semantic versioning)
    3. Update version in detected/configured files
    4. Commit version changes
    5. Create annotated git tag
    6. Push changes and tag to GitHub
    7. Monitor GitHub Actions release workflow
    8. Apply release notes after CI creates the release
    9. Report success with release URL

REQUIREMENTS:
    - git (with GitHub remote configured)
    - gh CLI (GitHub CLI) - for monitoring workflow
    - jq (for JSON processing, optional)

EOF
    exit 0
}

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1" >&2
}

log_step() {
    echo -e "\n${BLUE}▶${NC} ${BLUE}$1${NC}"
}

# Error handler
error_exit() {
    log_error "$1"
    exit 1
}

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -n|--no-push)
                NO_PUSH=true
                shift
                ;;
            --notes-file)
                if [[ -z "${2:-}" ]]; then
                    error_exit "--notes-file requires a file path argument"
                fi
                NOTES_FILE="$2"
                shift 2
                ;;
            --skip-checks)
                SKIP_CHECKS=true
                shift
                ;;
            -*)
                error_exit "Unknown option: $1. Use --help for usage information."
                ;;
            *)
                if [[ -z "$VERSION" ]]; then
                    VERSION="$1"
                else
                    error_exit "Multiple version arguments provided. Use --help for usage information."
                fi
                shift
                ;;
        esac
    done

    if [[ -z "$VERSION" ]]; then
        error_exit "Version argument is required. Use --help for usage information."
    fi
}

# Validate version format
validate_version() {
    local version="$1"

    # Remove 'v' prefix if present
    version="${version#v}"

    # Semantic versioning regex
    local semver_regex='^([0-9]+)\.([0-9]+)\.([0-9]+)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$'

    if [[ ! "$version" =~ $semver_regex ]]; then
        error_exit "Invalid version format: $version. Must follow semantic versioning (e.g., 1.2.3, 1.0.0-beta.1)"
    fi

    log_success "Version format valid: $version" >&2
    echo "$version"
}

# Check prerequisites
check_prerequisites() {
    log_step "Checking prerequisites"

    if ! command -v git &> /dev/null; then
        error_exit "git is not installed"
    fi
    log_success "git is installed"

    if ! command -v gh &> /dev/null; then
        log_warning "gh CLI is not installed - workflow monitoring will be skipped"
    else
        log_success "gh CLI is installed"
    fi

    if ! command -v jq &> /dev/null; then
        log_warning "jq is not installed - JSON processing may be limited"
    else
        log_success "jq is installed"
    fi

    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        error_exit "Not in a git repository"
    fi
    log_success "In git repository"

    if ! git remote get-url origin &> /dev/null; then
        error_exit "No 'origin' remote configured"
    fi
    log_success "GitHub remote configured"
}

# Check git status
check_git_status() {
    if [[ "$SKIP_CHECKS" == "true" ]]; then
        log_warning "Skipping git status checks (--skip-checks enabled)"
        return
    fi

    log_step "Checking git repository status"

    if [[ -n $(git status --porcelain) ]]; then
        log_error "Working directory has uncommitted changes:"
        git status --short
        error_exit "Commit or stash changes before releasing"
    fi
    log_success "Working directory is clean"

    log_info "Fetching latest from remote..."
    git fetch origin

    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)

    if ! git rev-parse --verify "origin/$current_branch" &> /dev/null; then
        error_exit "Current branch '$current_branch' doesn't exist on remote. Push it first."
    fi
    log_success "Current branch exists on remote"

    local local_commit remote_commit
    local_commit=$(git rev-parse HEAD)
    remote_commit=$(git rev-parse "origin/$current_branch")

    if [[ "$local_commit" != "$remote_commit" ]]; then
        log_error "Local branch is not in sync with remote"

        if git merge-base --is-ancestor HEAD "origin/$current_branch"; then
            error_exit "Local branch is behind remote. Pull latest changes first."
        fi

        if git merge-base --is-ancestor "origin/$current_branch" HEAD; then
            error_exit "Local branch is ahead of remote. Push changes first."
        fi

        error_exit "Local and remote branches have diverged. Resolve conflicts first."
    fi
    log_success "Local branch is in sync with remote"
}

# Check if tag already exists
check_tag_exists() {
    local tag="$1"

    log_step "Checking if tag exists"

    if git rev-parse "$tag" &> /dev/null; then
        error_exit "Tag $tag already exists locally"
    fi

    if git ls-remote --tags origin | grep -q "refs/tags/$tag"; then
        error_exit "Tag $tag already exists on remote"
    fi

    log_success "Tag $tag does not exist"
}

# Load project configuration
load_config() {
    local config_file="$PROJECT_ROOT/.release.conf"
    if [[ -f "$config_file" ]]; then
        log_info "Loading configuration from .release.conf"
        # shellcheck source=/dev/null
        source "$config_file"
    fi
}

# Auto-detect version files if not configured
detect_version_files() {
    if [[ ${#VERSION_FILES[@]} -gt 0 ]]; then
        log_info "Using configured VERSION_FILES (${#VERSION_FILES[@]} files)"
        return
    fi

    log_info "Auto-detecting version files..."

    # package.json at root
    if [[ -f "$PROJECT_ROOT/package.json" ]]; then
        VERSION_FILES+=("package.json")
    fi

    # package.json in workspace directories (one level deep)
    for pkg in "$PROJECT_ROOT"/*/package.json "$PROJECT_ROOT"/apps/*/package.json "$PROJECT_ROOT"/packages/*/package.json; do
        if [[ -f "$pkg" ]]; then
            local rel_path="${pkg#"$PROJECT_ROOT"/}"
            # Avoid duplicating root package.json
            if [[ "$rel_path" != "package.json" ]]; then
                VERSION_FILES+=("$rel_path")
            fi
        fi
    done

    # Cargo.toml at root
    if [[ -f "$PROJECT_ROOT/Cargo.toml" ]]; then
        VERSION_FILES+=("Cargo.toml")
    fi

    # pyproject.toml at root
    if [[ -f "$PROJECT_ROOT/pyproject.toml" ]]; then
        VERSION_FILES+=("pyproject.toml")
    fi

    if [[ ${#VERSION_FILES[@]} -eq 0 ]]; then
        log_warning "No version files detected. Only git tag will be created."
    else
        log_success "Detected ${#VERSION_FILES[@]} version file(s):"
        for f in "${VERSION_FILES[@]}"; do
            log_info "  $f"
        done
    fi
}

# Update a single version file
update_version_file() {
    local file="$1"
    local version="$2"
    local full_path="$PROJECT_ROOT/$file"

    if [[ ! -f "$full_path" ]]; then
        log_warning "File not found, skipping: $file"
        return
    fi

    case "$file" in
        *.json)
            # JSON files (package.json, plugin.json, etc.)
            if command -v jq &> /dev/null; then
                local tmp_file
                tmp_file=$(mktemp)
                jq --arg ver "$version" '.version = $ver' "$full_path" > "$tmp_file"
                mv "$tmp_file" "$full_path"
                log_success "Updated $file"
            else
                # Fallback: sed-based replacement
                sed -i '' 's/"version"[[:space:]]*:[[:space:]]*"[^"]*"/"version": "'"$version"'"/' "$full_path" 2>/dev/null || \
                sed -i 's/"version"[[:space:]]*:[[:space:]]*"[^"]*"/"version": "'"$version"'"/' "$full_path"
                log_success "Updated $file (sed fallback)"
            fi
            ;;
        Cargo.toml)
            # Rust Cargo.toml — update the first version field in [package]
            sed -i '' 's/^version[[:space:]]*=[[:space:]]*"[^"]*"/version = "'"$version"'"/' "$full_path" 2>/dev/null || \
            sed -i 's/^version[[:space:]]*=[[:space:]]*"[^"]*"/version = "'"$version"'"/' "$full_path"
            log_success "Updated $file"
            ;;
        pyproject.toml)
            # Python pyproject.toml
            sed -i '' 's/^version[[:space:]]*=[[:space:]]*"[^"]*"/version = "'"$version"'"/' "$full_path" 2>/dev/null || \
            sed -i 's/^version[[:space:]]*=[[:space:]]*"[^"]*"/version = "'"$version"'"/' "$full_path"
            log_success "Updated $file"
            ;;
        *.go)
            # Go files — update Version = "X.Y.Z" or version = "X.Y.Z" patterns
            sed -i '' 's/\(Version[[:space:]]*=[[:space:]]*\)"[^"]*"/\1"'"$version"'"/' "$full_path" 2>/dev/null || \
            sed -i 's/\(Version[[:space:]]*=[[:space:]]*\)"[^"]*"/\1"'"$version"'"/' "$full_path"
            log_success "Updated $file"
            ;;
        *)
            log_warning "Unknown file type, skipping: $file"
            ;;
    esac
}

# Update version references across the project
update_versions() {
    local version="$1"

    log_step "Updating version references"

    for file in "${VERSION_FILES[@]}"; do
        update_version_file "$file" "$version"
    done
}

# Commit version changes
commit_version_changes() {
    local version="$1"

    log_step "Committing version changes"

    # Stage all version files
    for file in "${VERSION_FILES[@]}"; do
        git add "$PROJECT_ROOT/$file" 2>/dev/null || true
    done

    if [[ -z $(git diff --cached --name-only) ]]; then
        log_warning "No version changes to commit"
        return
    fi

    local commit_msg
    commit_msg="chore: bump version to $version

Prepare for release v$version"

    git commit -m "$commit_msg"
    log_success "Committed version changes"
}

# Create git tag
create_git_tag() {
    local version="$1"
    local tag="v$version"

    log_step "Creating git tag $tag"

    local tag_msg="Release $tag"

    git tag -a "$tag" -m "$tag_msg"
    log_success "Created tag $tag"
}

# Apply release notes to the GitHub release created by CI
update_release_notes() {
    local version="$1"
    local tag="v$version"
    local notes_file="$2"

    if ! command -v gh &> /dev/null; then
        log_warning "gh CLI not available - cannot update release notes"
        log_info "Update release notes manually at the GitHub releases page"
        return 0
    fi

    log_step "Updating release notes"

    gh release edit "$tag" --notes-file "$notes_file"
    log_success "Release notes applied to $tag"
}

# Push changes
push_changes() {
    local version="$1"
    local tag="v$version"

    log_step "Pushing changes to GitHub"

    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)

    log_info "Pushing branch $current_branch..."
    git push origin "$current_branch"
    log_success "Pushed branch $current_branch"

    log_info "Pushing tag $tag..."
    git push origin "$tag"
    log_success "Pushed tag $tag"
}

# Monitor GitHub Actions workflow
monitor_workflow() {
    local version="$1"
    local tag="v$version"

    if ! command -v gh &> /dev/null; then
        log_warning "gh CLI not available - cannot monitor workflow"
        log_info "Check workflow status manually on GitHub Actions"
        return 0
    fi

    log_step "Monitoring GitHub Actions workflow"

    log_info "Waiting for workflow to start..."
    sleep 5

    # Try to find a release workflow
    local workflow_id
    workflow_id=$(gh run list --workflow=release.yml --limit=1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || echo "")

    # Fallback: try release.yaml
    if [[ -z "$workflow_id" ]]; then
        workflow_id=$(gh run list --workflow=release.yaml --limit=1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || echo "")
    fi

    if [[ -z "$workflow_id" ]]; then
        log_warning "Could not find a release workflow run"
        log_info "If you have a release workflow, check GitHub Actions manually"
        return 0
    fi

    log_info "Workflow started (ID: $workflow_id)"
    log_info "Watching workflow progress..."

    if gh run watch "$workflow_id" --exit-status; then
        log_success "Workflow completed successfully!"
        return 0
    else
        log_error "Workflow failed or was cancelled"
        local workflow_url
        workflow_url=$(gh run view "$workflow_id" --json url --jq '.url' 2>/dev/null || echo "Check GitHub Actions")
        log_error "Check details at: $workflow_url"
        return 1
    fi
}

# Get release URL
get_release_url() {
    local version="$1"
    local tag="v$version"

    if command -v gh &> /dev/null; then
        gh release view "$tag" --json url --jq '.url' 2>/dev/null && return
    fi

    local repo_url
    repo_url=$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | sed 's/\.git$//')
    echo "https://github.com/$repo_url/releases/tag/$tag"
}

# Rollback on failure
rollback() {
    local version="$1"
    local tag="v$version"

    log_warning "Release failed. Rolling back changes..."

    # Delete local tag if it exists
    if git rev-parse "$tag" &> /dev/null; then
        git tag -d "$tag" 2>/dev/null || true
        log_info "Deleted local tag $tag"
    fi

    # Warn about remote tag
    if [[ "$NO_PUSH" == "false" ]] && git ls-remote --tags origin | grep -q "refs/tags/$tag"; then
        log_warning "Tag was pushed to remote. You may want to delete it manually:"
        log_info "  git push origin :refs/tags/$tag"
    fi

    # Reset version commit if it was made
    if git log -1 --pretty=%B | grep -q "chore: bump version to $version"; then
        git reset --soft HEAD~1
        log_info "Reset version commit (changes are staged)"
    fi
}

# Main release process
main() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         Release Script                 ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}\n"

    parse_args "$@"

    # Normalize version (remove 'v' prefix)
    local clean_version
    clean_version=$(validate_version "$VERSION")
    local tag="v$clean_version"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_warning "DRY RUN MODE - No changes will be made"
    fi

    log_info "Release version: $clean_version"
    log_info "Git tag: $tag"
    echo ""

    # Change to project root
    cd "$PROJECT_ROOT"

    # Load config and detect files
    load_config
    detect_version_files

    # Pre-flight checks
    check_prerequisites
    check_git_status
    check_tag_exists "$tag"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_success "\nDry run completed successfully!"
        log_info "Run without --dry-run to create the release"
        exit 0
    fi

    # Confirm with user
    echo ""
    read -p "$(echo -e "${YELLOW}Create release $tag? [y/N]:${NC} ")" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Release cancelled"
        exit 0
    fi

    # Validate notes file if pushing
    if [[ "$NO_PUSH" == "false" && -z "$NOTES_FILE" ]]; then
        error_exit "Release notes are required. Provide --notes-file <path> with release notes."
    fi

    if [[ -n "$NOTES_FILE" && ! -f "$NOTES_FILE" ]]; then
        error_exit "Notes file not found: $NOTES_FILE"
    fi

    # Perform release
    local release_failed=false
    local workflow_failed=false

    {
        update_versions "$clean_version"
        commit_version_changes "$clean_version"
        create_git_tag "$clean_version"

        if [[ "$NO_PUSH" == "false" ]]; then
            push_changes "$clean_version"

            if ! monitor_workflow "$clean_version"; then
                workflow_failed=true
            fi

            if [[ "$workflow_failed" == "false" && -n "$NOTES_FILE" ]]; then
                update_release_notes "$clean_version" "$NOTES_FILE"
            fi
        else
            log_warning "Skipping push (--no-push enabled)"
            log_info "To push manually: git push origin $(git rev-parse --abbrev-ref HEAD) && git push origin $tag"
        fi
    } || {
        release_failed=true
    }

    if [[ "$release_failed" == "true" ]]; then
        rollback "$clean_version"
        error_exit "Release failed"
    fi

    # Report results
    echo ""
    if [[ "$workflow_failed" == "true" ]]; then
        echo -e "${YELLOW}╔════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║   Tag Pushed but Workflow Failed!     ║${NC}"
        echo -e "${YELLOW}╚════════════════════════════════════════╝${NC}\n"

        log_warning "Version: $clean_version"
        log_warning "Tag: $tag (pushed successfully)"
        log_error "GitHub Actions workflow failed"

        local repo_url
        repo_url=$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | sed 's/\.git$//')
        log_info "Check workflow at: https://github.com/$repo_url/actions"
        log_info "Fix the issue and re-run the workflow, or delete the tag to retry:"
        log_info "  git tag -d $tag"
        log_info "  git push origin :refs/tags/$tag"

        exit 1
    else
        echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║     Release Created Successfully!     ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════╝${NC}\n"

        log_success "Version: $clean_version"
        log_success "Tag: $tag"

        if [[ "$NO_PUSH" == "false" ]]; then
            local release_url
            release_url=$(get_release_url "$clean_version")
            log_success "Release URL: $release_url"
        fi

        echo ""
    fi
}

# Run main
main "$@"
