# FAZRI — Entity Enrollment Runbook

**Audience**: University IT administrators setting up FAZRI for the first time.
**Time to complete**: 2–4 hours for a campus with 1–3 buildings.

---

## Prerequisites

Before starting, make sure you have:

- [ ] FAZRI stack running (`docker compose -f docker-compose.prod.yml up -d` completed successfully)
- [ ] Admin login credentials for the FAZRI web interface
- [ ] An SAP export of student/staff data (CSV format — see Step 1 for required columns)
- [ ] Admin access to the Hikvision NVR web panel (if you have RFID door readers)
- [ ] Admin access to the Aruba wireless controller (if you have Aruba WiFi)
- [ ] Physical access to the campus for the end-to-end verification walk (Step 7)

---

## Step 1 — Import entity master data

This populates FAZRI with the names, IDs, and roles of everyone on campus. Without this step, the system cannot associate sensor events with people.

### 1a. Export from SAP (or similar HR system)

Export a CSV with these columns (column names are flexible — FAZRI will auto-detect common variants):

| Column | Required? | Example |
|--------|-----------|---------|
| `entity_id` or `employee_no` | Yes | `S2024001` |
| `name` | Yes | `Rajesh Kumar` |
| `role` or `designation` | Yes | `student` / `staff` / `faculty` |
| `email` | Recommended | `rajesh@campus.edu` |
| `department` | Recommended | `Computer Science` |
| `student_id` or `employee_no` | Recommended | `2024CS001` |
| `card_id` | Optional | RFID card number |
| `mac_address` or `device_hash` | Optional | WiFi device MAC |

Save as UTF-8 encoded CSV (not Excel .xlsx).

### 1b. Import via API

**Option A — Web UI (recommended):**
1. Log into the FAZRI dashboard
2. Go to **Admin → Import → SAP CSV**
3. Upload the CSV file
4. Review the preview and click **Import**

**Option B — Command line:**
```bash
# From inside the backend container
docker compose -f docker-compose.prod.yml exec backend \
  python scripts/sap_csv_import.py /app/augmented/your_export.csv

# With dry-run to preview before committing
docker compose -f docker-compose.prod.yml exec backend \
  python scripts/sap_csv_import.py /app/augmented/your_export.csv --dry-run
```

**Option C — API call:**
```bash
curl -X POST https://your-domain.edu/api/v1/import/sap-csv \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -F "file=@/path/to/your_export.csv"
```

### 1c. Verify

- Go to **Dashboard → Entity Search**
- Search for a known name — the entity should appear
- Check the count: the import result shows how many were created vs. updated

---

## Step 2 — Configure zone mapping

Zones connect physical locations (doors, APs, cameras) to meaningful place names in FAZRI.

### 2a. Decide your zone IDs

Pick short, descriptive IDs — no spaces, uppercase recommended:

| Physical Location | Suggested zone_id |
|-------------------|--------------------|
| Library entrance | `LIB_ENT` |
| Computer lab, floor 1 | `LAB_CSE_1F` |
| Cafeteria | `CAFETERIA` |
| Admin block lobby | `ADMIN_LOBBY` |
| Auditorium | `AUDITORIUM` |

### 2b. Map Hikvision door readers → zone_ids

Find the door number for each reader in the Hikvision web panel:
- Log into the NVR → **Access Control** → **Door Management**
- Note the door number (1, 2, 3...) for each physical door

Then set the mapping in `.env.prod`:
```env
HIKVISION_DOOR_ZONE_MAP={"1":"LIB_ENT","2":"LAB_CSE_1F","3":"CAFETERIA","4":"ADMIN_LOBBY"}
```

### 2c. Map Aruba APs → zone_ids

Get AP names from the Aruba controller:
- Log into the Aruba controller → **Monitoring** → **Access Points**
- Note the AP name (e.g., `AP-LIB-1F-01`) for APs in each zone

Then set the mapping in `.env.prod`:
```env
ARUBA_AP_ZONE_MAP={"AP-LIB-1F-01":"LIB_ENT","AP-CSE-1F-01":"LAB_CSE_1F","AP-CAFE-01":"CAFETERIA"}
```

### 2d. (Optional) Update zone travel times

Edit `backend/config/zone_matrix.py` to add your campus zones with GPS coordinates.
FAZRI uses the coordinates to automatically calculate how long it should take to walk between zones. The default values work for a typical campus, but you can tune them.

```python
"LIB_ENT": ZoneConfig(
    zone_id="LIB_ENT",
    name="Library Entrance",
    building="Main Library",
    floor="0",
    lat=20.1234,   # <-- replace with actual GPS
    lon=85.5678,
),
```

After editing, restart the backend:
```bash
docker compose -f docker-compose.prod.yml restart backend
```

---

## Step 3 — Connect Hikvision access control

### 3a. Find the NVR credentials

In the Hikvision NVR web interface:
- Default IP is usually `192.168.1.64` (check with your network team)
- Admin username: `admin` (default)
- The NVR must be on the same network as the FAZRI server

### 3b. Test the connection

```bash
# Replace 192.168.1.64 with your NVR IP
curl -u admin:YOUR_NVR_PASSWORD \
  http://192.168.1.64/ISAPI/System/deviceInfo \
  --digest
```

You should see XML with the device model and serial number. If you get a 401, check the password.

### 3c. Enable polling

Edit `.env.prod`:
```env
HIKVISION_ENABLED=true
HIKVISION_BASE_URL=http://192.168.1.64
HIKVISION_USERNAME=admin
HIKVISION_PASSWORD=your_nvr_password
HIKVISION_POLL_INTERVAL_SECONDS=5
```

Restart the backend:
```bash
docker compose -f docker-compose.prod.yml restart backend
```

### 3d. Verify

- In the FAZRI dashboard, go to **Sensor Events** (live feed)
- Swipe an RFID card at any door
- Within 5 seconds, an `ACCESS_GRANTED` or `ACCESS_DENIED` event should appear

---

## Step 4 — Connect Aruba WiFi

### 4a. Find the controller credentials

- Controller IP: Ask your network team (typically `192.168.1.1` or similar)
- Create a read-only API user in the Aruba controller:
  - AOS8: **Configuration** → **Management** → **Administrators** → Add user with "read-only" role
  - Note the username and password

### 4b. Test the connection

```bash
# Get API token
# IMPORTANT: Use HTTPS — credentials are sent as query parameters per the AOS8 API spec
# and will appear in plaintext in HTTP access logs if TLS is not enforced.
curl -X POST "https://ARUBA_IP/v1/api/login?username=YOUR_USER&password=YOUR_PASSWORD"
```

You should get a response with `"status":"Success"` and a `UIDARUBA` token.

### 4c. Enable polling

Edit `.env.prod`:
```env
ARUBA_ENABLED=true
ARUBA_BASE_URL=https://192.168.1.1
ARUBA_USERNAME=fazri_readonly
ARUBA_PASSWORD=your_aruba_password
ARUBA_POLL_INTERVAL_SECONDS=30
```

Restart the backend:
```bash
docker compose -f docker-compose.prod.yml restart backend
```

### 4d. Verify

- In the FAZRI dashboard, go to **Sensor Events**
- Connect a phone to the campus WiFi
- Within 30 seconds, a `DEVICE_ASSOCIATED` event should appear (if the device's MAC address is in the entity database)

---

## Step 5 — Set up cameras

### 5a. Add camera streams

1. Log into the FAZRI dashboard
2. Go to **Camera Streams** (in the sidebar)
3. Click **Add Stream**
4. Enter the RTSP URL of your camera, e.g.:
   ```bash
   rtsp://admin:password@192.168.1.101:554/Streaming/Channels/101
   ```
5. Set the Zone ID for this camera (e.g., `LIB_ENT`)
6. Click **Save & Test**

### 5b. Verify the live view

- Click the camera card to open the live WebRTC view
- The stream should appear within 5-10 seconds

### 5c. Face recognition starts automatically

Once a camera stream is active and at least one face is enrolled (Step 6), the DeepFace server begins processing the stream. No additional configuration is needed.

---

## Step 6 — Enroll faces

### 6a. Find the entity

1. Go to **Dashboard** → search for the person by name
2. Open their entity profile
3. Click **Face Enrollment**

### 6b. Upload photos

- Upload **3–5 clear photos** of the person's face
- Photo requirements:
  - Face clearly visible and unobstructed
  - Good lighting (no strong shadows)
  - Different angles work well (front, slight left, slight right)
  - JPG or PNG, at least 200×200 pixels
- Click **Enroll** after each photo

### 6c. Verify enrollment

- After uploading, click **Test Recognition**
- Upload a new photo of the same person — the system should match them with >70% confidence

---

## Step 7 — Verify end-to-end

This is the final check that everything works together.

### 7a. RFID test
1. Have a person whose RFID card is in the database swipe at a door
2. Wait 5 seconds
3. In FAZRI → **Sensor Events**: look for an `ACCESS_GRANTED` event with their name resolved

### 7b. WiFi test
1. Have that person connect their registered device to campus WiFi
2. Wait 30 seconds
3. In **Sensor Events**: look for a `DEVICE_ASSOCIATED` event with their name resolved

### 7c. Camera test
1. Have that person walk past a camera zone
2. Wait 10-20 seconds
3. In **Sensor Events**: look for a `FACE_RECOGNIZED` event with their name

### 7d. Multi-modal timeline
1. Go to **Dashboard** → search for the person → open their entity profile
2. Scroll to **Movement Timeline**
3. You should see all three event types — RFID, WiFi, Camera — for that person

If you see all three, the system is working correctly.

---

## Troubleshooting

### No events appearing in Sensor Events

| Symptom | Check |
|---------|-------|
| No RFID events | Is `HIKVISION_ENABLED=true`? Check backend logs: `docker logs fazri_backend` |
| No WiFi events | Is `ARUBA_ENABLED=true`? Can the backend reach the controller IP? |
| No Camera events | Is the camera stream active? Check **Camera Streams** page |
| Events appear but name is "Unresolved" | Was the entity imported? Check entity search by card ID or MAC |

### Check backend logs
```bash
docker compose -f docker-compose.prod.yml logs -f backend --tail=100
```

### Check a specific service
```bash
# Is PostgreSQL running?
docker compose -f docker-compose.prod.yml exec postgres pg_isready

# Is Redis running?
docker compose -f docker-compose.prod.yml exec redis redis-cli ping

# Is DeepFace server running?
curl http://localhost:8000/api/v1/system/health
```

### Health check endpoints
| Endpoint | What it checks |
|----------|----------------|
| `GET /health` | Backend is alive |
| `GET /api/v1/system/health` | All subsystem statuses |

### Log file locations (inside backend container)
```bash
/app/logs/          — application logs
/var/log/nginx/     — nginx access and error logs (in nginx container)
```

### Reset and re-import
If you need to re-import the entity database from scratch:
```bash
# WARNING: This deletes all existing entity data
docker compose -f docker-compose.prod.yml exec backend python scripts/reset_entity_data.py --confirm
# Then re-run the import
```
