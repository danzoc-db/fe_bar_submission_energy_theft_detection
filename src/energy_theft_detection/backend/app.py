import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .._metadata import app_name, dist_dir
from .config import AppConfig
from .logger import logger
from .lakebase_client import LakebaseClient
from .router import api, _warm_cache, _check_schema_access
from .sql_client import SQLClient
from .utils import add_not_found_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = AppConfig()
    logger.info(f"Starting {config.app_name}")
    logger.info(f"Catalog: {config.catalog}.{config.schema_name}")
    logger.info(f"SQL Warehouse: {config.sql_warehouse_id or '(not configured)'}")
    logger.info(f"AI Gateway: {config.ai_gateway_endpoint}")

    if config.sql_warehouse_id:
        try:
            sql_client = SQLClient(config)
            app.state.sql_client = sql_client
            logger.info("SQL Warehouse client initialised")

            if not config.workspace_url:
                try:
                    host = str(sql_client._client.config.host).rstrip("/")
                    import os
                    os.environ["DATABRICKS_HOST"] = host
                    logger.info(f"Derived DATABRICKS_HOST from SDK profile: {host}")
                except Exception:
                    pass

            ok, err = _check_schema_access(sql_client)
            if ok:
                logger.info("Schema access check passed")
                t0 = time.monotonic()
                _warm_cache(sql_client)
                logger.info(f"Cache warmed in {round((time.monotonic() - t0) * 1000)}ms")
            else:
                logger.error(
                    f"SCHEMA ACCESS CHECK FAILED — cache NOT warmed.\n{err}\n"
                    "The /readiness endpoint will auto-retry and warm cache on success."
                )
        except Exception as e:
            logger.warning(f"SQL Warehouse client failed to initialise: {e}")
            app.state.sql_client = None
    else:
        logger.warning("SQL_WAREHOUSE_ID not set — SQL queries disabled")
        app.state.sql_client = None

    # Lakebase operational-serving client (optional). Health check is lazy, so
    # construction is cheap even when disabled; the Delta path is unaffected.
    app.state.lakebase_client = None
    if config.lakebase_enabled:
        try:
            app.state.lakebase_client = LakebaseClient(config)
            logger.info(
                f"Lakebase client initialised (instance={config.lakebase_instance_name})"
            )
        except Exception as e:
            logger.warning(f"Lakebase client failed to initialise: {e}")
    else:
        logger.info("Lakebase disabled (LAKEBASE_ENABLED not set) — Delta-only path")

    app.state.config = config
    yield


app = FastAPI(title=app_name, lifespan=lifespan)
ui = StaticFiles(directory=dist_dir, html=True)

app.include_router(api)
app.mount("/", ui)

add_not_found_handler(app)
