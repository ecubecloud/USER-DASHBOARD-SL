import os
import requests
import logging
import json
import time
from datetime import datetime, timedelta, timezone

import firebase_admin
from firebase_admin import credentials, firestore

# -------------------------------
# Configuration & Logging Setup
# -------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
file_handler = logging.FileHandler("output.txt")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

CLIENT_ID = os.getenv("STARLINK_CLIENT_ID", "b2b070d3-4fa6-41f0-8266-f8c2643e0016")
CLIENT_SECRET = os.getenv("STARLINK_CLIENT_SECRET", "Ghana@2029@!--Ghana@2029@!$$Ghana@2029@!")

token_cache = {"access_token": None}

# -------------------------------
# Firebase Initialization
# -------------------------------
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), 'starlink-48ae3-firebase-adminsdk-fbsvc-c263e8cc3f.json')
cred = credentials.Certificate(CREDENTIALS_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()

# -------------------------------
# API Client Functions
# -------------------------------
def fetch_access_token():
    try:
        response = requests.post(
            'https://api.starlink.com/auth/connect/token',
            headers={'Content-type': 'application/x-www-form-urlencoded'},
            data={
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'grant_type': 'client_credentials',
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        access_token = data.get('access_token')
        if not access_token:
            raise ValueError("Access token not received in the response.")
        token_cache["access_token"] = access_token
        logger.info("Access token updated successfully.")
    except Exception as e:
        logger.error(f"Error fetching access token: {e}")
        raise

def get_header():
    if not token_cache["access_token"]:
        fetch_access_token()
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {token_cache['access_token']}"
    }

def make_authorized_request(url, method, **kwargs):
    try:
        kwargs['headers'] = get_header()
        response = requests.request(method, url, **kwargs, timeout=10)
        if response.status_code == 401:
            logger.info("Access token expired or unauthorized; refreshing token.")
            fetch_access_token()
            kwargs['headers'] = get_header()
            response = requests.request(method, url, **kwargs, timeout=10)
        response.raise_for_status()
        return response
    except Exception as e:
        logger.error(f"Error during request to {url}: {e}")
        raise

def fetch_all_pages(url, method='GET', params=None, data=None, json_data=None, **kwargs):
    if method.upper() == 'GET':
        if params is None:
            params = {}
        page = params.get('page', 0)
        limit = params.get('limit', 50)
    elif method.upper() == 'POST':
        if json_data is None:
            json_data = {}
        page = json_data.get('pageIndex', 0)
        limit = json_data.get('pageLimit', 50)
    else:
        page = 0
        limit = 50

    all_items = []
    while True:
        if method.upper() == 'GET':
            params['page'] = page
            params['limit'] = limit
        elif method.upper() == 'POST':
            json_data['pageIndex'] = page
            json_data['pageLimit'] = limit

        response = make_authorized_request(url, method, params=params, data=data, json=json_data, **kwargs)
        result = response.json()
        logger.info(f"Page {page} response: {result}")

        if isinstance(result, dict):
            if "results" in result:
                items = result.get("results", [])
            elif "content" in result and isinstance(result["content"], dict):
                items = result["content"].get("results", [])
            else:
                items = result.get('items') or result.get('data') or []
        elif isinstance(result, list):
            items = result
        else:
            items = []

        all_items.extend(items)

        if isinstance(result, dict) and "content" in result:
            if result["content"].get("isLastPage", False) or len(items) < limit:
                break
        elif len(items) < limit:
            break

        page += 1

    return all_items

# -------------------------------
# Firestore Storage Functions
# -------------------------------
def update_if_changed(doc_ref, new_data, merge=False):
    """
    Updates a document in Firestore only if 'new_data' differs from what's already stored.
    """
    try:
        existing = doc_ref.get()
        if existing.exists:
            existing_data = existing.to_dict()
            if json.dumps(existing_data, sort_keys=True) == json.dumps(new_data, sort_keys=True):
                logger.info(f"Document {doc_ref.id} unchanged, skipping update")
                return False
            else:
                doc_ref.set(new_data, merge=merge)
                logger.info(f"Document {doc_ref.id} updated with new data")
                return True
        else:
            doc_ref.set(new_data)
            logger.info(f"Document {doc_ref.id} created with new data")
            return True
    except Exception as e:
        logger.error(f"Error updating document {doc_ref.id}: {e}")
        raise

def store_account(account_data):
    try:
        doc_ref = db.collection('accounts').document(account_data.get('accountNumber'))
        new_data = {
            "account_name": account_data.get("accountName"),
            "account_number": account_data.get("accountNumber"),
            "region_code": account_data.get("regionCode")
        }
        update_if_changed(doc_ref, new_data)
        logger.info(f"Stored account {account_data.get('accountNumber')}")
    except Exception as e:
        logger.error(f"Error storing account: {e}")

def store_billing_record_global(record):
    """
    Store billing record in a top-level 'billing_records' collection for dashboard compatibility.
    Document ID is a combination of serviceLineNumber, startDate, and endDate.
    """
    try:
        service_line = record.get("serviceLineNumber", "unknown")
        start_date = record.get("startDate", "unknown")
        end_date = record.get("endDate", "unknown")
        doc_id = f"{service_line}_{start_date}_{end_date}"
        doc_ref = db.collection('billing_records').document(doc_id)
        update_if_changed(doc_ref, record)
    except Exception as e:
        logger.error(f"Error storing global billing record for service line {record.get('serviceLineNumber')}: {e}")

def store_billing_record(account_number, record):
    try:
        service_line = record.get("serviceLineNumber", "unknown")
        subcollection = f"billing_records_{service_line}"
        billing_doc_id = f"{record.get('startDate')}_{record.get('endDate')}"
        doc_ref = db.collection('accounts').document(account_number).collection(subcollection).document(billing_doc_id)
        update_if_changed(doc_ref, record)
        # Also store in global collection for dashboard compatibility
        store_billing_record_global(record)
    except Exception as e:
        logger.error(f"Error storing billing record for service line {record.get('serviceLineNumber')}: {e}")

def store_address(address_data):
    try:
        doc_id = address_data.get('addressReferenceId')
        if not doc_id:
            logger.error("Address missing reference ID")
            return
        doc_ref = db.collection('addresses').document(doc_id)
        update_if_changed(doc_ref, address_data)
    except Exception as e:
        logger.error(f"Error storing address: {e}")

def store_single_address(address_data):
    try:
        content = address_data.get("content", address_data)
        doc_id = content.get('addressReferenceId', 'unknown')
        doc_ref = db.collection('addresses').document(doc_id)
        update_if_changed(doc_ref, content, merge=True)
    except Exception as e:
        logger.error(f"Error storing single address: {e}")

def store_router_configs(configs):
    try:
        for config in configs:
            doc_id = config.get('configId')
            if not doc_id:
                continue
            doc_ref = db.collection('router_configs').document(doc_id)
            update_if_changed(doc_ref, config)
    except Exception as e:
        logger.error(f"Error storing router configs: {e}")

def store_single_router_config(config_data):
    try:
        content = config_data.get("content", config_data)
        doc_id = content.get('configId', 'unknown')
        doc_ref = db.collection('router_configs').document(doc_id)
        new_config = json.loads(content.get('routerConfigJson', '{}'))
        new_data = {
            'configJSON': new_config,
            'lastUpdated': firestore.SERVER_TIMESTAMP
        }
        update_if_changed(doc_ref, new_data, merge=True)
    except Exception as e:
        logger.error(f"Error storing single router config: {e}")

def store_service_lines(service_lines):
    try:
        for line in service_lines:
            doc_id = line.get('serviceLineNumber')
            if not doc_id:
                continue
            doc_ref = db.collection('service_lines').document(doc_id)
            update_if_changed(doc_ref, line)
    except Exception as e:
        logger.error(f"Error storing service lines: {e}")

def store_single_service_line(line_data):
    try:
        content = line_data.get("content", line_data)
        doc_id = content.get('serviceLineNumber', 'unknown')
        doc_ref = db.collection('service_lines').document(doc_id)
        update_if_changed(doc_ref, content)
    except Exception as e:
        logger.error(f"Error storing single service line: {e}")

def store_user_terminals(user_terminals):
    try:
        for ut in user_terminals:
            doc_id = ut.get('userTerminalId')
            if doc_id:
                doc_ref = db.collection('user_terminals').document(doc_id)
                update_if_changed(doc_ref, ut)
    except Exception as e:
        logger.error(f"Error storing user terminals: {e}")

def fix_nested_arrays(data):
    if isinstance(data, list):
        new_list = []
        for element in data:
            if isinstance(element, list):
                new_list.append(json.dumps(element))
            else:
                new_list.append(fix_nested_arrays(element))
        return new_list
    elif isinstance(data, dict):
        return {k: fix_nested_arrays(v) for k, v in data.items()}
    else:
        return data

# -------------------------------
# Telemetry Storage & Aggregation
# -------------------------------
def commit_batch(batch, attempt=1, max_attempts=3):
    try:
        batch.commit()
    except Exception as e:
        if attempt < max_attempts:
            wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds...
            time.sleep(wait_time)
            return commit_batch(batch, attempt + 1, max_attempts)
        else:
            raise e

def store_telemetry(telemetry_data):
    try:
        data = telemetry_data.get("data", {})
        values = data.get("values", [])
        column_names = data.get("columnNamesByDeviceType", {})

        max_batch_size = 200
        batch = db.batch()
        writes_in_batch = 0


        routers_encountered = set()

        for record in values:
            if not record:
                continue

            device_type = record[0]
            cols = column_names.get(device_type, [])
            record_dict = dict(zip(cols, record))

            # Convert UtcTimestampNs -> ISO8601
            utc_timestamp_ns = record_dict.get("UtcTimestampNs")
            if utc_timestamp_ns:
                ts_seconds = int(utc_timestamp_ns) // 1_000_000_000
                dt_utc = datetime.fromtimestamp(ts_seconds, tz=timezone.utc)
                iso_str = dt_utc.isoformat()
                record_dict["timestamp"] = iso_str

            # Identify router
            router_id = record_dict.get("DeviceId")
            if not router_id:
                continue


            routers_encountered.add(router_id)

            # Construct doc ID from UtcTimestampNs to avoid duplicates
            if utc_timestamp_ns:
                doc_id = str(utc_timestamp_ns)
            else:
                doc_id = db.collection("telemetry_raw").document(router_id).collection("records").document().id

            doc_ref = (
                db.collection("telemetry_raw")
                .document(router_id)
                .collection("records")
                .document(doc_id)
            )

            batch.set(doc_ref, record_dict)
            writes_in_batch += 1

            if writes_in_batch >= max_batch_size:
                commit_batch(batch)
                batch = db.batch()
                writes_in_batch = 0

        if writes_in_batch > 0:
            commit_batch(batch)

        for r_id in routers_encountered:
            prune_old_records(r_id, keep_count=30)
        

        logger.info("Stored telemetry data (appended as new docs).")

    except Exception as e:
        logger.error(f"Error storing telemetry: {e}")

# ---------------------------------------------------------
# Aggregation
# ---------------------------------------------------------
def prune_old_records(router_id, keep_count=30):
    try:
        subcol_ref = db.collection("telemetry_raw").document(router_id).collection("records")
        old_records_query = (
            subcol_ref
            .order_by("UtcTimestampNs", direction=firestore.Query.DESCENDING)
            .offset(keep_count)  # skip the newest 'keep_count'
        )
        
        # We can delete in batches of (say) 200 to avoid batch-size limits
        max_batch_size = 200
        batch = db.batch()
        writes_in_batch = 0
        
        for doc_snapshot in old_records_query.stream():
            batch.delete(doc_snapshot.reference)
            writes_in_batch += 1
            
            if writes_in_batch >= max_batch_size:
                batch.commit()
                batch = db.batch()
                writes_in_batch = 0
        
        # Commit any remaining deletes in the batch
        if writes_in_batch > 0:
            batch.commit()

        logger.info(f"Pruned old records for router {router_id}, kept the latest {keep_count} docs.")
    except Exception as e:
        logger.error(f"Error pruning old records for router {router_id}: {e}")


def aggregate_time_window(collection_name, minutes):
    try:
        now = datetime.now(timezone.utc)
        # Round to minute
        end = now.replace(second=0, microsecond=0)
        start = end - timedelta(minutes=minutes)

        total_ping = 0.0
        total_signal = 0.0
        total_count = 0

        # Iterate all router docs
        router_docs = db.collection("telemetry_raw").stream()
        for router_doc in router_docs:
            subcol_ref = router_doc.reference.collection("records")
            # Query for timestamp in [start, end)
            query = (
                subcol_ref
                .filter("timestamp", ">=", start.isoformat())
                .filter("timestamp", "<", end.isoformat())
            )
            for rec_doc in query.stream():
                rec_data = rec_doc.to_dict()
                try:
                    ping = float(rec_data.get("PingLatencyMsAvg", 0))
                    signal = float(rec_data.get("SignalQuality", 0))
                except:
                    ping = 0
                    signal = 0
                total_ping += ping
                total_signal += signal
                total_count += 1

        if total_count > 0:
            agg_data = {
                "timestamp": end.isoformat(),
                "avg_ping": total_ping / total_count,
                "avg_signal": total_signal / total_count,
                "count": total_count
            }
            db.collection(collection_name).document(end.isoformat()).set(agg_data)
            logger.info(f"Aggregated {minutes} minutes into {collection_name}: {agg_data}")
        else:
            logger.info(f"No data found in last {minutes} minutes for aggregator {collection_name}.")
    except Exception as e:
        logger.error(f"Error aggregating {collection_name}: {e}")

def aggregate_15m():
    """Aggregate last 15 minutes -> 'telemetry_15m'."""
    aggregate_time_window("telemetry_15m", 15)

def aggregate_3h():
    """Aggregate last 180 minutes -> 'telemetry_3h'."""
    aggregate_time_window("telemetry_3h", 180)

def aggregate_1d():
    """Aggregate last 1440 minutes (1 day) -> 'telemetry_1d'."""
    aggregate_time_window("telemetry_1d", 1440)

def aggregate_7d():
    """Aggregate last 10080 minutes (7 days) -> 'telemetry_7d'."""
    aggregate_time_window("telemetry_7d", 10080)

def aggregate_30d():
    """Aggregate last 43200 minutes (30 days) -> 'telemetry_30d'."""
    aggregate_time_window("telemetry_30d", 43200)

# -------------------------------
# Endpoints Update Functions (1-9)
# -------------------------------
def update_endpoints():
    """Fetch and update endpoints 1-9 in Firestore (accounts, billing, addresses, router configs, service lines, user terminals)."""
    results = {}
    # Endpoint 1: Accounts
    try:
        logger.info("Endpoint 1: Fetching accounts...")
        url_accounts = "https://web-api.starlink.com/enterprise/v1/accounts"
        params_accounts = {"limit": 50, "page": 0}
        accounts = fetch_all_pages(url_accounts, method='GET', params=params_accounts)
        results["accounts"] = accounts
        logger.info(f"Fetched {len(accounts)} accounts.")
        for acc in accounts:
            store_account(acc)
    except Exception as e:
        logger.error(f"Error in Endpoint 1 (accounts): {e}")

    # Endpoint 2: Billing Cycles
    try:
        logger.info("Endpoint 2: Fetching billing cycles...")
        url_billing = "https://web-api.starlink.com/enterprise/v1/accounts/ACC-4570165-26134-9/billing-cycles/query"
        billing_payload = {
            "previousBillingCycles": 8,
            "pageIndex": 0,
            "pageLimit": 50,
        }
        all_billing_records = fetch_all_pages(url_billing, method='POST', json_data=billing_payload)
        logger.info(f"Billing cycles fetched: {all_billing_records}")
        for record in all_billing_records:
            store_billing_record("ACC-4570165-26134-9", record)
        results["billing_cycles"] = all_billing_records
        logger.info(f"Total billing records fetched: {len(all_billing_records)}")
    except Exception as e:
        logger.error(f"Error in Endpoint 2 (billing cycles): {e}")

    # Endpoint 3: Addresses
    try:
        logger.info("Endpoint 3: Fetching addresses...")
        url_addresses = "https://web-api.starlink.com/enterprise/v1/account/ACC-4570165-26134-9/addresses"
        params_addresses = {"limit": 50, "page": 0}
        addresses = fetch_all_pages(url_addresses, method='GET', params=params_addresses)
        results["addresses"] = addresses
        logger.info(f"Fetched {len(addresses)} addresses.")
        for addr in addresses:
            store_address(addr)
    except Exception as e:
        logger.error(f"Error in Endpoint 3 (addresses): {e}")

    # Endpoint 4: Single Address
    try:
        logger.info("Endpoint 4: Fetching single address...")
        address_reference_id = "5dc3e828-eac9-4ffa-94e8-c85fd0394fbd"
        url_single_address = f"https://web-api.starlink.com/enterprise/v1/account/ACC-4570165-26134-9/addresses/{address_reference_id}"
        response_address = make_authorized_request(url_single_address, method='GET')
        single_address = response_address.json()
        results["single_address"] = single_address
        store_single_address(single_address)
    except Exception as e:
        logger.error(f"Error in Endpoint 4 (single address): {e}")

    # Endpoint 5: Router Configs
    try:
        logger.info("Endpoint 5: Fetching router configs...")
        url_routers = "https://web-api.starlink.com/enterprise/v1/account/ACC-4570165-26134-9/routers/configs"
        params_routers = {"page": 0, "limit": 50}
        routers_configs = fetch_all_pages(url_routers, method='GET', params=params_routers)
        results["routers_configs"] = routers_configs
        store_router_configs(routers_configs)
    except Exception as e:
        logger.error(f"Error in Endpoint 5 (router configs): {e}")

    # Endpoint 6: Single Router Config
    try:
        logger.info("Endpoint 6: Fetching single router config...")
        config_id = "DVC_CFG-28159-32854-41"
        url_single_router = f"https://web-api.starlink.com/enterprise/v1/account/ACC-4570165-26134-9/routers/configs/{config_id}"
        response_router = make_authorized_request(url_single_router, method='GET')
        single_router_config = response_router.json()
        results["single_router_config"] = single_router_config
        store_single_router_config(single_router_config)
    except Exception as e:
        logger.error(f"Error in Endpoint 6 (single router config): {e}")

    # Endpoint 7: Service Lines
    try:
        logger.info("Endpoint 7: Fetching service lines...")
        url_service_lines = "https://web-api.starlink.com/enterprise/v1/account/ACC-4570165-26134-9/service-lines"
        params_service_lines = {"limit": 50, "page": 0}
        service_lines = fetch_all_pages(url_service_lines, method='GET', params=params_service_lines)
        results["service_lines"] = service_lines
        store_service_lines(service_lines)
    except Exception as e:
        logger.error(f"Error in Endpoint 7 (service lines): {e}")

    # Endpoint 8: Single Service Line
    try:
        logger.info("Endpoint 8: Fetching single service line...")
        service_line = "SL-3734495-34282-79"
        url_single_service_line = f"https://web-api.starlink.com/enterprise/v1/account/ACC-4570165-26134-9/service-lines/{service_line}"
        response_service_line = make_authorized_request(url_single_service_line, method='GET')
        single_service_line_data = response_service_line.json()
        results["single_service_line"] = single_service_line_data
        store_single_service_line(single_service_line_data)
    except Exception as e:
        logger.error(f"Error in Endpoint 8 (single service line): {e}")

    # Endpoint 9: User Terminals
    try:
        logger.info("Endpoint 9: Fetching user terminals...")
        url_user_terminals = "https://web-api.starlink.com/enterprise/v1/account/ACC-4570165-26134-9/user-terminals"
        params_user_terminals = {"limit": 50, "page": 0}
        user_terminals = fetch_all_pages(url_user_terminals, method='GET', params=params_user_terminals)
        results["user_terminals"] = user_terminals
        store_user_terminals(user_terminals)
    except Exception as e:
        logger.error(f"Error in Endpoint 9 (user terminals): {e}")

# -------------------------------
# Telemetry Update Function (Endpoint 10)
# -------------------------------
def update_telemetry():
    try:
        logger.info("Endpoint 10: Fetching telemetry...")
        url_telemetry = "https://web-api.starlink.com/telemetry/stream/v1/telemetry"
        telemetry_payload = {
            "accountNumber": "ACC-4570165-26134-9",
            "batchSize": 4000,
            "maxLingerMs": 15000
        }
        response_telemetry = make_authorized_request(url=url_telemetry, method='POST', json=telemetry_payload)
        telemetry_data = response_telemetry.json()
        store_telemetry(telemetry_data)
    except Exception as e:
        logger.error(f"Error in Endpoint 10 (telemetry): {e}")

# -------------------------------
# Scheduler & Main Loop
# -------------------------------
def main():
    # Example: One-time run
    update_endpoints()
    # update_telemetry()
    # aggregate_15m()
    # aggregate_1h()
    # If you want to do repeated scheduling, un-comment and install "schedule" package:
    # schedule.every(1).hours.do(update_endpoints)
    # schedule.every(15).seconds.do(update_telemetry)
    # schedule.every(1).minutes.do(cleanup_old_telemetry)
    # schedule.every(1).minutes.do(aggregate_telemetry_1m)
    # schedule.every(5).minutes.do(aggregate_telemetry_5m)
    # schedule.every(15).minutes.do(aggregate_telemetry_15m)
    # schedule.every(60).minutes.do(aggregate_telemetry_1h)

    # logger.info("Scheduler started. Running tasks as scheduled...")
    # while True:
    #     schedule.run_pending()
    #     time.sleep(1)
    pass

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Service stopped by user.")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
