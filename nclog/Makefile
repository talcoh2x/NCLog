TEST_PATH=./
APP_DIR := ${CURDIR}
SRC_DIR := ${APP_DIR}/src
UTILS_DIR := ${APP_DIR}/utils
TARGET_API := ${APP_DIR}/nclog
DIST_DIR := ${APP_DIR}/dist
BIN_DIR := ${APP_DIR}/bin

WS := ${APP_DIR}/../

mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))

clean-pyc:
	find . -name '*.pyc' -exec rm --force {} +
	find . -name '*.pyo' -exec rm --force {} +
	find . -name '*.spec' -exec rm --force {} +

clean-build:
	rm --force --recursive build/
	rm --force --recursive bin/
	rm --force --recursive dist/
	rm --force --recursive *.egg-info

clean: clean-pyc clean-build


build:
	mkdir -p ${BIN_DIR}
	pyinstaller --paths=${SRC_DIR} --paths=${UTILS_DIR} \
		--onefile --add-data="${UTILS_DIR}/dmesg_patterns:data_files" --add-data="${UTILS_DIR}/sw_patterns:data_files" ${TARGET_API}
	mv ${DIST_DIR}/nclog ${BIN_DIR}
	rm -rf ${DIST_DIR} ${APP_DIR}/build
	rm -rf *.spec

install: clean build

SOURCEDIR = bin
SOURCES := $(shell find $(SOURCEDIR) -name '*')

OBJS :=$(foreach dir,$(SOURCEDIR),$(wildcard $(dir)/*))

test: $(OBJS)
	$^ -h

.PHONY: clean-pyc clean-build


.PHONY: help

# Show this help.
help:
	@echo "    install"
	@echo "        Clean and build all"
	@echo "    clean"
	@echo "        calling to clean-pyc & clean-build"
	@echo "    clean-pyc"
	@echo "        Remove python artifacts."
	@echo "    clean-build"
	@echo "        Remove build artifacts."
	@echo "    test"
	@echo "        Run all test from <<${SOURCEDIR}>>"
	

