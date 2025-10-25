# Campus Zones & Anomaly Detection Guide

## Overview
This document describes the 12 campus zones configured in the system and the types of anomalies that can be demonstrated with these zones and occupancy patterns.

---

## Zone Definitions

### 1. ADMIN_LOBBY
- **Type**: LOBBY (Public Common Area)
- **Capacity**: 50
- **Operating Hours**: 08:00 - 18:00
- **Access Level**: PUBLIC
- **Security Level**: LOW
- **Peak Hours**: 9, 10, 11, 14, 15, 16, 17
- **WiFi APs**: AP_ADMIN_1 through AP_ADMIN_5
- **Actual Data**: 4,055 card swipes

**Normal Pattern**:
- Weekday: Busy 8-18 (peak 15:00 with ~45 people), dead 19-07
- Weekend: Minimal activity (max 8 people at 11:00)

**Anomaly Examples**:
- ❌ Access at 2 AM (should be 0)
- ❌ 100+ people (over capacity)
- ❌ Weekend evening activity

---

### 2. AUDITORIUM
- **Type**: AUDITORIUM (Event Space)
- **Capacity**: 300
- **Operating Hours**: 08:00 - 22:00
- **Access Level**: BOOKING_REQUIRED
- **Security Level**: MEDIUM
- **Peak Hours**: 10, 11, 14, 15, 16, 19, 20
- **WiFi APs**: AP_AUD_1 through AP_AUD_5
- **Actual Data**: 4,049 card swipes, 4,117 bookings

**Normal Pattern**:
- Weekday: Classes 10-12 (250 people), seminars 14-17 (270 peak), events 19-21 (200)
- Weekend: Events only (10-21, 80-180 people)
- Dead hours: 0-7, 23

**Anomaly Examples**:
- ❌ 250 people at 3 AM (closed + suspicious)
- ❌ Activity without booking
- ❌ Access during dead hours (midnight-7 AM)

---

### 3. CAF_01
- **Type**: CAFETERIA (Dining)
- **Capacity**: 250
- **Operating Hours**: 06:30 - 23:00
- **Access Level**: PUBLIC
- **Security Level**: LOW
- **Peak Hours**: 7, 8, 12, 13, 14, 19, 20, 21
- **WiFi APs**: AP_CAF_1 through AP_CAF_5
- **Actual Data**: 4,049 card swipes

**Normal Pattern**:
- Three meal peaks: Breakfast (8:00, 120), Lunch (13:00, 220), Dinner (19:00, 170)
- Weekend: Brunch pattern (delayed morning)
- Off-peak: 30-50 people

**Anomaly Examples**:
- ❌ 200 people at 3 AM (closed)
- ❌ Zero activity during lunch (12-14) on weekday
- ❌ Overcapacity (>250)

---

### 4. GYM
- **Type**: GYM (Recreation)
- **Capacity**: 80
- **Operating Hours**: 05:00 - 23:00
- **Access Level**: MEMBERSHIP_REQUIRED
- **Security Level**: MEDIUM
- **Peak Hours**: 6, 7, 8, 17, 18, 19, 20, 21
- **WiFi APs**: AP_GYM_1, AP_GYM_2
- **Actual Data**: 3,968 card swipes

**Normal Pattern**:
- Strong morning peak: 6-8 (58 people at 7 AM)
- Strong evening peak: 17-21 (75 people at 18:00)
- Low midday: 10-15 (8-18 people)

**Anomaly Examples**:
- ❌ Non-member access
- ❌ 100 people (overcapacity)
- ❌ Access 1-4 AM (closed)
- ❌ High activity at 2 PM (should be ~12)

---

### 5. HOSTEL_GATE
- **Type**: ENTRANCE (Security Checkpoint)
- **Capacity**: 30
- **Operating Hours**: 24/7
- **Access Level**: RESIDENT_ONLY
- **Security Level**: HIGH
- **Curfew**: 23:00
- **Peak Hours**: 7, 8, 9, 17, 18, 19, 20, 21, 22, 23
- **WiFi APs**: AP_HOSTEL_1 through AP_HOSTEL_5
- **Actual Data**: 3,980 card swipes

**Normal Pattern**:
- Morning exodus: 7-9 (28 people at 8 AM)
- Evening return: 17-23 (28 at 18:00)
- Post-curfew: 0-2 people (highly restricted)

**Anomaly Examples**:
- ❌ Non-resident access
- ❌ Multiple entries after curfew (23:00)
- ❌ 50+ people at once (overcapacity)
- ❌ Non-student in restricted hostel area

---

### 6. LAB_101
- **Type**: LAB (Computer Science)
- **Capacity**: 40
- **Operating Hours**: 07:00 - 21:00
- **Access Level**: STUDENT_FACULTY
- **Security Level**: MEDIUM
- **Department**: CSE
- **Peak Hours**: 9, 10, 11, 14, 15, 16, 17, 18
- **WiFi APs**: AP_LAB_1, AP_LAB_2
- **Actual Data**: 3,992 card swipes, 3,857 bookings

**Normal Pattern**:
- Class hours: 9-12 (39 peak), 14-18 (38 peak)
- Evening taper: 18-21 (22→8→2)
- Strictly closed: 21:00-07:00 (0 people)

**Anomaly Examples**:
- ❌ Access at 2 AM (closed, security breach)
- ❌ 60 people (overcapacity)
- ❌ Access without booking
- ❌ Non-CSE student during restricted hours

---

### 7. LAB_102
- **Type**: LAB (Engineering)
- **Capacity**: 35
- **Operating Hours**: 08:00 - 20:00
- **Access Level**: STUDENT_FACULTY
- **Security Level**: MEDIUM
- **Department**: MECH
- **Peak Hours**: 9, 10, 11, 14, 15, 16
- **WiFi APs**: AP_LAB_3
- **Actual Data**: 4,097 bookings

**Normal Pattern**:
- Weekday: 9-12 (32 peak), 14-17 (30 peak)
- Closed: 20:00-08:00
- Weekend: Minimal (8-18 people max)

**Anomaly Examples**:
- ❌ Access at midnight (closed)
- ❌ 50 people (overcapacity)
- ❌ High activity on Sunday (should be minimal)

---

### 8. LAB_305
- **Type**: LAB (Electronics)
- **Capacity**: 30
- **Operating Hours**: 08:00 - 19:00
- **Access Level**: DEPARTMENT_RESTRICTED
- **Security Level**: HIGH
- **Department**: ECE
- **Restricted to**: ECE, EEE, Physics only
- **Peak Hours**: 10, 11, 14, 15, 16
- **WiFi APs**: AP_LAB_4, AP_LAB_5
- **Actual Data**: 3,909 card swipes, 3,847 bookings

**Normal Pattern**:
- Strict hours: 8-19 only (28 people peak at 11/15)
- Completely closed: 19:00-08:00 (0 tolerance)
- Weekend: Faculty/grad only (3-8 people)

**Anomaly Examples**:
- ❌ CSE student access (department restricted)
- ❌ Any access 19:00-08:00 (HIGH SECURITY ALERT)
- ❌ Unauthorized department access
- ❌ Weekend undergrad access

---

### 9. LIB_ENT
- **Type**: ENTRANCE (Library Access)
- **Capacity**: 25
- **Operating Hours**: 07:00 - 23:00
- **Access Level**: STUDENT_FACULTY
- **Security Level**: MEDIUM
- **Quiet Hours**: After 20:00
- **Peak Hours**: 9, 10, 11, 14, 15, 16, 17, 18, 19, 20
- **WiFi APs**: AP_LIB_1 through AP_LIB_5
- **Actual Data**: 3,998 card swipes, 28,000 book checkouts

**Normal Pattern**:
- Steady 9-20 (22-25 people)
- Late night study: 20-23 (18→10→4)
- Closed: 23:00-07:00

**Anomaly Examples**:
- ❌ Access at 4 AM (closed)
- ❌ 50+ people queued (overcapacity)
- ❌ Multiple book checkouts without entry swipe

---

### 10. SEM_01
- **Type**: SEMINAR_ROOM (Meeting Space)
- **Capacity**: 60
- **Operating Hours**: 08:00 - 20:00
- **Access Level**: BOOKING_REQUIRED
- **Security Level**: LOW
- **Peak Hours**: 9, 10, 11, 14, 15, 16
- **WiFi APs**: AP_SEM_1
- **Actual Data**: 4,062 bookings

**Normal Pattern**:
- Weekday: Classes 9-12 (50 peak), 14-17 (48 peak)
- Closed: 20:00-08:00
- Weekend: Study groups (15-35 people, 10-17)

**Anomaly Examples**:
- ❌ 60 people without booking
- ❌ Access at 2 AM (closed)
- ❌ Sustained overnight occupancy

---

### 11. ROOM_A1
- **Type**: MEETING_ROOM (Faculty/Staff Only)
- **Capacity**: 20
- **Operating Hours**: 08:00 - 18:00
- **Access Level**: FACULTY_STAFF (No students!)
- **Security Level**: MEDIUM
- **Peak Hours**: 9, 10, 11, 14, 15, 16
- **WiFi APs**: AP_ADMIN_2
- **Actual Data**: 4,016 bookings

**Normal Pattern**:
- Weekday: 9-17 only (15 people peak at 15:00)
- Strictly closed: 18:00-08:00 and all weekend
- Weekend: Essentially empty (1-2 people max)

**Anomaly Examples**:
- ❌ Student access (role violation)
- ❌ Access at 10 PM (closed)
- ❌ Weekend heavy usage
- ❌ Booking by non-faculty/staff

---

### 12. ROOM_A2
- **Type**: MEETING_ROOM (Faculty/Staff Only)
- **Capacity**: 20
- **Operating Hours**: 08:00 - 18:00
- **Access Level**: FACULTY_STAFF
- **Security Level**: MEDIUM
- **Peak Hours**: 9, 10, 11, 14, 15, 16
- **WiFi APs**: AP_ADMIN_3
- **Actual Data**: 4,004 bookings

**Normal Pattern**: (Same as ROOM_A1)

**Anomaly Examples**: (Same as ROOM_A1)

---

## Anomaly Detection Scenarios

### 1. Temporal Anomalies
**Off-hours Access**:
- LAB_305 at 2 AM → CRITICAL (high security lab)
- ADMIN_LOBBY at 11 PM → ALERT (should be empty)
- GYM at 3 AM → ALERT (closed)

**Wrong Day Patterns**:
- ROOM_A1 busy on Sunday → ALERT (staff room, weekend closed)
- High auditorium occupancy without weekend event → SUSPICIOUS

### 2. Occupancy Anomalies
**Overcapacity**:
- 100 people in GYM (capacity 80) → ALERT
- 400 people in Auditorium (capacity 300) → CRITICAL

**Undercapacity** (when should be busy):
- 5 people in cafeteria at 1 PM weekday → UNUSUAL
- 0 people in library during exam week 3 PM → SUSPICIOUS

### 3. Access Control Anomalies
**Role-based Violations**:
- Student E100001 in ROOM_A1 → ALERT (faculty/staff only)
- Non-ECE student in LAB_305 → ALERT (department restricted)
- Non-resident at HOSTEL_GATE → SECURITY BREACH

**Post-curfew Violations**:
- HOSTEL_GATE access after 23:00 → POLICY VIOLATION
- Multiple late entries → PATTERN ALERT

### 4. Behavioral Anomalies
**Impossible Travel**:
- Entity at HOSTEL_GATE at 9:00, LAB_101 at 9:02 → IMPOSSIBLE (same user, different zones, too fast)

**Unusual Duration**:
- 18 hours continuous in LAB_101 → HEALTH CONCERN
- 30 minutes in GYM every day for month, then 4 hours → UNUSUAL SPIKE

**Frequency Anomalies**:
- Card swipe every 5 minutes at different locations → BOT/FRAUD
- Same person entering cafeteria 8 times in one day → UNUSUAL

### 5. Multi-modal Anomalies
**WiFi-Card Mismatch**:
- Card swipe at LAB_101 but WiFi at AUDITORIUM → LOCATION CONFLICT
- No card swipe but WiFi presence → TAILGATING

**CCTV-Card Mismatch**:
- Card swipe with face_id=F100001 but CCTV shows different face → IDENTITY FRAUD
- Multiple faces detected but single card swipe → TAILGATING

**Booking Anomalies**:
- Occupancy in AUDITORIUM without booking → UNAUTHORIZED USE
- Booking for 50 people but only 5 showed → RESOURCE WASTE
- No-show pattern → ACCOUNTABILITY ISSUE

### 6. Department-based Anomalies
**Cross-department Access**:
- Physics student in LAB_305 (ECE-only) → VERIFY (allowed)
- CIVIL student in LAB_305 → ALERT (not in restricted_departments)

### 7. Seasonal/Contextual Anomalies
**Exam Period**:
- Low library occupancy → SUSPICIOUS
- High late-night lab use → EXPECTED

**Holiday Period**:
- High campus activity → SUSPICIOUS
- Faculty access to restricted areas → EXPECTED (maintenance)

---

## Visualization Examples

### Occupancy Heatmap
```
Hour  | LAB_101 | CAF_01 | GYM | HOSTEL
------|---------|--------|-----|--------
00:00 |    0    |   2    |  0  |   2
06:00 |    0    |   5    | 35  |   8
09:00 |   36    |  95    | 20  |  20
12:00 |   18    | 180    | 15  |   6
15:00 |   37    |  45    | 18  |   5
18:00 |   22    |  65    | 75  |  28
21:00 |    2    |  85    | 42  |  18
23:00 |    0    |   8    |  5  |  12
```

### Anomaly Severity Levels
1. **CRITICAL**: LAB_305 access outside hours, HOSTEL non-resident access
2. **HIGH**: Role violations, department restrictions, overcapacity >150%
3. **MEDIUM**: Off-hours in public areas, unusual patterns
4. **LOW**: Minor deviations, first-time occurrences

---

## Sample Queries for Anomaly Detection

### 1. Off-hours Access Detection
```cypher
MATCH (sa:SpatialActivity)-[:OCCURRED_IN]->(z:Zone)
WHERE sa.hour < 8 OR sa.hour > 20
  AND z.zone_id IN ['LAB_101', 'LAB_305', 'ROOM_A1']
RETURN sa, z
```

### 2. Occupancy Anomalies
```cypher
MATCH (sa:SpatialActivity)-[:OCCURRED_IN]->(z:Zone)
WHERE sa.occupancy > z.capacity * 1.2  // 120% capacity
RETURN z.zone_id, sa.timestamp, sa.occupancy, z.capacity
ORDER BY sa.occupancy DESC
```

### 3. Department Violations
```cypher
MATCH (e:Entity)-[:ACCESSED]->(z:Zone {zone_id: 'LAB_305'})
WHERE NOT e.department IN ['ECE', 'EEE', 'Physics']
RETURN e.entity_id, e.department, z.zone_id
```

---

## Dataset Statistics

- **Total Zones**: 12
- **Total Entities**: 7,000 (5,601 students, 681 faculty, 718 staff)
- **Departments**: 10 (CSE, ECE, EEE, MECH, CIVIL, Physics, Chemistry, Maths, BIO, Admin)
- **Card Swipes**: 32,000
- **CCTV Frames**: 28,000
- **Lab Bookings**: 28,000
- **Library Checkouts**: 28,000
- **WiFi Associations**: 32,000
- **WiFi Access Points**: 35 (distributed across zones)

## Implementation Notes

This configuration creates:
- **Clear normal patterns** with specific peak hours
- **Dead zones** (0 activity) for easy anomaly detection
- **Access restrictions** by role, department, time
- **Capacity constraints** for overcrowding detection
- **Multi-modal data** for cross-validation
- **Realistic campus behavior** based on actual data distribution
