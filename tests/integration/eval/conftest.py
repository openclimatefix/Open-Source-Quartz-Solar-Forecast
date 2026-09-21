# import pytest

# @pytest.mark.parametrize("folder_name", ["30_minutely", "5_minutely"])
# def test_folder_processing(folder_name):
#     """
#     Run tests for both folder types using parameterization.
#     """
#     print(f"Running tests for folder: {folder_name}")
#     assert folder_name in ["30_minutely", "5_minutely"]

import pytest

def pytest_addoption(parser):
    """Add custom command line option for folder name"""
    parser.addoption(
        "--foldername",
        action="store",
        default=None,
        help="Specify the folder name: 30_minutely or 5_minutely"
    )

def pytest_generate_tests(metafunc):
    """Generate test parameters based on command line option"""
    if "folder_name" in metafunc.fixturenames:
        foldername = metafunc.config.getoption("foldername")
        if foldername:
            # Run only for specified folder
            metafunc.parametrize("folder_name", [foldername])
        else:
            # Run for both folders (default)
            metafunc.parametrize("folder_name", ["30_minutely", "5_minutely"])