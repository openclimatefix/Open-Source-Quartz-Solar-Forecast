
import os
import sys
import pickle
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_models")

# Add current directory to path
sys.path.append(os.getcwd())

import quartz_solar_forecast.forecasts.v1 as v1

try:
    from psp.serialization import load_model
    # We might need to save it manually if psp doesn't expose save_model
    # or if we want to ensure latest protocol.
    # checking if psp has save_model? likely yes.
    try:
        from psp.serialization import save_model
    except ImportError:
        save_model = None

except ImportError as e:
    logger.error(f"Failed to import psp: {e}")
    sys.exit(1)

MODELS_DIR = "quartz_solar_forecast/models"
MODELS_TO_MIGRATE = ["model-0.3.0.pkl", "model-0.4.0.pkl"]

def migrate_model(filename):
    path = os.path.join(MODELS_DIR, filename)
    if not os.path.exists(path):
        logger.warning(f"Model file not found: {path} - Skipping")
        return

    logger.info(f"Loading model: {path}")
    try:
        # Load the model (this deserializes it using current installed libraries)
        model = load_model(path)
        logger.info(f"Successfully loaded {filename}. Re-saving...")

        # Re-save the model
        # If psp has save_model, use it. Otherwise use pickle.dump
        if save_model:
             save_model(model, path)
        else:
            with open(path, "wb") as f:
                pickle.dump(model, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        logger.info(f"Successfully re-saved {filename}")

    except Exception as e:
        logger.error(f"Failed to migrate {filename}: {e}")
        # Make a backup just in case we corrupted something? 
        # Actually we load then save, so prompt failure happens before write.
        raise e

if __name__ == "__main__":
    logger.info(f"Python Version: {sys.version}")
    
    for model_file in MODELS_TO_MIGRATE:
        migrate_model(model_file)
    
    logger.info("Migration completed.")
