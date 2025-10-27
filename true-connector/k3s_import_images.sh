#!/bin/bash

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# List of rdlabengpa images to import
declare -a IMAGES=(
    "rdlabengpa/ids_execution_core_container:v1.14.8"
    "rdlabengpa/ids_uc_data_app_platoon:v1.7.9"
    "rdlabengpa/ids_be_data_app:v0.3.8"
    "rdlabengpa/ids_uc_data_app_platoon_pip:v1.0.0"
)

# Additional images you might want to import (uncomment to include)
#declare -a ADDITIONAL_IMAGES=(
    "ids-connector-toe:v1.0.0"
    "allenabishek/ids-connector-sdt:v1.0.0"
    "ids-connector-sdt:v1.0.0"
    "arq101/sdt-main-image:v0.2.1"
    "sdt-main-image:v0.2.1"
#)

# Function to check if k3s is available
check_k3s() {
    if ! command -v k3s &> /dev/null; then
        echo -e "${RED}Error: k3s is not installed or not in PATH${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ K3s detected${NC}"
}

# Function to check if docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker detected${NC}"
}

# Function to import a single image
import_image() {
    local image=$1
    echo -e "${BLUE}Processing: ${image}${NC}"
    
    # Check if image exists in docker
    if docker image inspect "${image}" &> /dev/null; then
        echo -e "${GREEN}  ✓ Image found in Docker${NC}"
        
        # Import to k3s
        echo -e "${YELLOW}  → Importing to K3s...${NC}"
        if docker save "${image}" | sudo k3s ctr images import - &> /dev/null; then
            echo -e "${GREEN}  ✓ Successfully imported: ${image}${NC}"
            return 0
        else
            echo -e "${RED}  ✗ Failed to import: ${image}${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}  ⚠ Image not found in Docker: ${image}${NC}"
        return 2
    fi
}

# Function to verify imported images
verify_imports() {
    echo -e "\n${BLUE}Verifying imported images in K3s...${NC}"
    sudo k3s ctr images list | grep rdlabengpa
}

# Main execution
main() {
    echo -e "${BLUE}===================================${NC}"
    echo -e "${BLUE}K3s Image Import Script${NC}"
    echo -e "${BLUE}===================================${NC}\n"
    
    # Check prerequisites
    check_docker
    check_k3s
    
    echo -e "\n${BLUE}Starting image import process...${NC}\n"
    
    # Statistics
    local total=0
    local success=0
    local failed=0
    local not_found=0
    
    # Import rdlabengpa images
    echo -e "${GREEN}Importing rdlabengpa images...${NC}\n"
    for image in "${IMAGES[@]}"; do
        ((total++))
        import_image "$image"
        case $? in
            0) ((success++)) ;;
            1) ((failed++)) ;;
            2) ((not_found++)) ;;
        esac
        echo ""
    done
    
    # Optional: Import additional images
    read -p "Do you want to import additional project images (ids-connector, sdt-main-image, etc.)? [y/N]: " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "\n${GREEN}Importing additional images...${NC}\n"
        for image in "${ADDITIONAL_IMAGES[@]}"; do
            ((total++))
            import_image "$image"
            case $? in
                0) ((success++)) ;;
                1) ((failed++)) ;;
                2) ((not_found++)) ;;
            esac
            echo ""
        done
    fi
    
    # Summary
    echo -e "${BLUE}===================================${NC}"
    echo -e "${BLUE}Import Summary${NC}"
    echo -e "${BLUE}===================================${NC}"
    echo -e "Total images processed: ${total}"
    echo -e "${GREEN}Successfully imported: ${success}${NC}"
    echo -e "${RED}Failed to import: ${failed}${NC}"
    echo -e "${YELLOW}Not found in Docker: ${not_found}${NC}"
    
    # Verify imports
    verify_imports
    
    # Final status
    if [ $failed -eq 0 ] && [ $not_found -eq 0 ]; then
        echo -e "\n${GREEN}✓ All images imported successfully!${NC}"
        exit 0
    elif [ $failed -gt 0 ]; then
        echo -e "\n${RED}✗ Some images failed to import. Please check the errors above.${NC}"
        exit 1
    else
        echo -e "\n${YELLOW}⚠ Import completed with warnings. Some images were not found.${NC}"
        exit 0
    fi
}

# Run main function
main