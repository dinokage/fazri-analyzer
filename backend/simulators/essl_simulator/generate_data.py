#!/usr/bin/env python3
"""
eSSL Card Reader Data Generator

Generates 90 days of realistic card swipe data for testing the data pipeline.
Creates temporal patterns, user behaviors, and occasional anomalies.
"""

import random
import mysql.connector
from datetime import datetime, timedelta
from typing import List, Tuple
import os


# Configuration
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', '3307'))
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', 'essl_password')
MYSQL_DB = os.getenv('MYSQL_DB', 'essl_db')

# Simulation parameters
NUM_STUDENTS = 300
NUM_FACULTY = 50
NUM_STAFF = 30
NUM_VISITORS = 20
DAYS_TO_GENERATE = 90

# Door IDs from init.sql
DOORS = [
    'MAIN_ENTRANCE',
    'LIBRARY_ENTRY',
    'LAB_BLOCK_A',
    'LAB_BLOCK_B',
    'CAFETERIA_ENTRY',
    'HOSTEL_GATE_1',
    'HOSTEL_GATE_2',
    'ADMIN_OFFICE',
    'SPORTS_COMPLEX',
    'RESEARCH_LAB'
]

# User behavior profiles
STUDENT_PATTERN = {
    'arrival_time': (8, 10),  # 8 AM - 10 AM
    'departure_time': (16, 20),  # 4 PM - 8 PM
    'weekend_probability': 0.3,  # 30% come on weekends
    'late_night_probability': 0.1,  # 10% stay late
    'avg_daily_swipes': 8,  # Average swipes per day
}

FACULTY_PATTERN = {
    'arrival_time': (8, 9),  # 8 AM - 9 AM
    'departure_time': (17, 19),  # 5 PM - 7 PM
    'weekend_probability': 0.4,  # 40% work on weekends
    'late_night_probability': 0.2,  # 20% work late
    'avg_daily_swipes': 6,
}

STAFF_PATTERN = {
    'arrival_time': (7, 8),  # 7 AM - 8 AM
    'departure_time': (16, 17),  # 4 PM - 5 PM
    'weekend_probability': 0.1,  # 10% work on weekends
    'late_night_probability': 0.05,  # 5% work late
    'avg_daily_swipes': 4,
}

VISITOR_PATTERN = {
    'arrival_time': (9, 14),  # 9 AM - 2 PM
    'departure_time': (11, 17),  # 11 AM - 5 PM
    'weekend_probability': 0.05,  # 5% come on weekends
    'late_night_probability': 0.0,
    'avg_daily_swipes': 2,
}


class User:
    """Represents a user with card access."""

    def __init__(self, user_id: str, name: str, card_no: str, role: str, department: str):
        self.user_id = user_id
        self.name = name
        self.card_no = card_no
        self.role = role
        self.department = department
        self.pattern = self._get_pattern()

    def _get_pattern(self):
        """Get behavior pattern based on role."""
        if self.role == 'Student':
            return STUDENT_PATTERN
        elif self.role == 'Faculty':
            return FACULTY_PATTERN
        elif self.role == 'Staff':
            return STAFF_PATTERN
        else:
            return VISITOR_PATTERN

    def should_be_present(self, date: datetime) -> bool:
        """Determine if user should be on campus on this date."""
        is_weekend = date.weekday() >= 5

        if is_weekend:
            return random.random() < self.pattern['weekend_probability']

        # Weekday - most people come, but some randomness
        return random.random() < 0.95

    def generate_daily_swipes(self, date: datetime) -> List[Tuple[datetime, str, str]]:
        """Generate swipe events for a single day."""
        if not self.should_be_present(date):
            return []

        swipes = []

        # Arrival time
        arrival_hour = random.randint(*self.pattern['arrival_time'])
        arrival_minute = random.randint(0, 59)
        arrival_time = date.replace(hour=arrival_hour, minute=arrival_minute, second=random.randint(0, 59))

        # Main entrance for arrival
        swipes.append((arrival_time, 'MAIN_ENTRANCE', 'IN'))

        # Generate movement around campus
        num_swipes = random.randint(
            max(1, self.pattern['avg_daily_swipes'] - 3),
            self.pattern['avg_daily_swipes'] + 3
        )

        current_time = arrival_time
        for _ in range(num_swipes):
            # Random movement every 1-3 hours
            current_time += timedelta(hours=random.randint(1, 3), minutes=random.randint(0, 59))

            # Don't go past departure time
            if current_time.hour >= self.pattern['departure_time'][1]:
                break

            # Choose a random door based on role
            door = self._choose_door()
            event_type = random.choice(['IN', 'OUT'])

            swipes.append((current_time, door, event_type))

        # Departure time
        departure_hour = random.randint(*self.pattern['departure_time'])

        # Late night work?
        if random.random() < self.pattern['late_night_probability']:
            departure_hour = random.randint(20, 23)

        departure_minute = random.randint(0, 59)
        departure_time = date.replace(hour=departure_hour, minute=departure_minute, second=random.randint(0, 59))

        swipes.append((departure_time, 'MAIN_ENTRANCE', 'OUT'))

        return swipes

    def _choose_door(self) -> str:
        """Choose a door based on user role."""
        if self.role == 'Student':
            # Students go to library, labs, cafeteria, sports
            return random.choice([
                'LIBRARY_ENTRY', 'LAB_BLOCK_A', 'LAB_BLOCK_B',
                'CAFETERIA_ENTRY', 'SPORTS_COMPLEX', 'HOSTEL_GATE_1'
            ])
        elif self.role == 'Faculty':
            # Faculty go to labs, offices, library
            return random.choice([
                'LIBRARY_ENTRY', 'LAB_BLOCK_A', 'LAB_BLOCK_B',
                'ADMIN_OFFICE', 'RESEARCH_LAB', 'CAFETERIA_ENTRY'
            ])
        elif self.role == 'Staff':
            # Staff mostly in admin areas
            return random.choice([
                'ADMIN_OFFICE', 'CAFETERIA_ENTRY', 'MAIN_ENTRANCE'
            ])
        else:
            # Visitors mostly main areas
            return random.choice([
                'ADMIN_OFFICE', 'LIBRARY_ENTRY', 'CAFETERIA_ENTRY'
            ])


def generate_users() -> List[User]:
    """Generate all user profiles."""
    users = []

    # Generate students
    departments = ['Computer Science', 'Electrical Engineering', 'Mechanical Engineering',
                   'Civil Engineering', 'Mathematics', 'Physics', 'Chemistry']

    for i in range(NUM_STUDENTS):
        user_id = f'S{i+1:04d}'
        card_no = f'CARD{i+1:06d}'
        name = f'Student {i+1}'
        department = random.choice(departments)
        users.append(User(user_id, name, card_no, 'Student', department))

    # Generate faculty
    for i in range(NUM_FACULTY):
        user_id = f'F{i+1:04d}'
        card_no = f'CARD{NUM_STUDENTS+i+1:06d}'
        name = f'Professor {i+1}'
        department = random.choice(departments)
        users.append(User(user_id, name, card_no, 'Faculty', department))

    # Generate staff
    staff_depts = ['Administration', 'Maintenance', 'Security', 'Library', 'IT Support']
    for i in range(NUM_STAFF):
        user_id = f'T{i+1:04d}'
        card_no = f'CARD{NUM_STUDENTS+NUM_FACULTY+i+1:06d}'
        name = f'Staff {i+1}'
        department = random.choice(staff_depts)
        users.append(User(user_id, name, card_no, 'Staff', department))

    # Generate visitors
    for i in range(NUM_VISITORS):
        user_id = f'V{i+1:04d}'
        card_no = f'CARD{NUM_STUDENTS+NUM_FACULTY+NUM_STAFF+i+1:06d}'
        name = f'Visitor {i+1}'
        users.append(User(user_id, name, card_no, 'Visitor', 'Guest'))

    return users


def insert_users(cursor, users: List[User]):
    """Insert users into database."""
    print(f"Inserting {len(users)} users...")

    for user in users:
        cursor.execute("""
            INSERT INTO Users (UserID, Name, CardNo, Department, Role, Active)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (user.user_id, user.name, user.card_no, user.department, user.role, True))

    print(f"✓ {len(users)} users inserted")


def generate_and_insert_events(cursor, users: List[User], start_date: datetime):
    """Generate and insert card swipe events for all users over 90 days."""
    print(f"Generating {DAYS_TO_GENERATE} days of card swipe events...")

    total_events = 0

    for day in range(DAYS_TO_GENERATE):
        current_date = start_date + timedelta(days=day)
        day_events = []

        # Generate events for all users on this day
        for user in users:
            swipes = user.generate_daily_swipes(current_date)
            day_events.extend([
                (user.user_id, user.card_no, swipe_time, door, event_type)
                for swipe_time, door, event_type in swipes
            ])

        # Sort by time
        day_events.sort(key=lambda x: x[2])

        # Insert day's events
        if day_events:
            cursor.executemany("""
                INSERT INTO AccessLogs (UserID, CardNo, AccessTime, DoorID, EventType, VerifyMode)
                VALUES (%s, %s, %s, %s, %s, 'CARD')
            """, day_events)

            total_events += len(day_events)

        # Progress update every 10 days
        if (day + 1) % 10 == 0:
            print(f"  Day {day + 1}/{DAYS_TO_GENERATE}: {total_events:,} events generated")

    print(f"✓ Total events generated: {total_events:,}")
    return total_events


def add_anomalies(cursor, users: List[User], start_date: datetime):
    """Add some anomalous events for testing anomaly detection."""
    print("Adding anomalous events for testing...")

    anomalies = []

    # 1. Late night access (unusual hours)
    suspicious_user = random.choice([u for u in users if u.role == 'Student'])
    for _ in range(5):
        random_day = random.randint(0, DAYS_TO_GENERATE - 1)
        anomaly_time = (start_date + timedelta(days=random_day)).replace(
            hour=random.randint(2, 4),
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        anomalies.append((
            suspicious_user.user_id,
            suspicious_user.card_no,
            anomaly_time,
            'RESEARCH_LAB',
            'IN'
        ))

    # 2. Multiple rapid swipes (tailgating)
    tailgater = random.choice([u for u in users if u.role == 'Visitor'])
    base_time = (start_date + timedelta(days=random.randint(20, 40))).replace(hour=14, minute=30)
    for i in range(10):
        anomalies.append((
            tailgater.user_id,
            tailgater.card_no,
            base_time + timedelta(minutes=i),
            'MAIN_ENTRANCE',
            'IN' if i % 2 == 0 else 'OUT'
        ))

    # 3. Weekend access by typically weekday-only users
    weekend_worker = random.choice([u for u in users if u.role == 'Staff'])
    for week in range(0, DAYS_TO_GENERATE // 7):
        saturday = start_date + timedelta(days=week * 7 + 5)  # Saturday
        sunday = start_date + timedelta(days=week * 7 + 6)    # Sunday

        for day in [saturday, sunday]:
            anomalies.append((
                weekend_worker.user_id,
                weekend_worker.card_no,
                day.replace(hour=random.randint(6, 8), minute=random.randint(0, 59)),
                'ADMIN_OFFICE',
                'IN'
            ))

    # Insert anomalies
    if anomalies:
        cursor.executemany("""
            INSERT INTO AccessLogs (UserID, CardNo, AccessTime, DoorID, EventType, VerifyMode)
            VALUES (%s, %s, %s, %s, %s, 'CARD')
        """, anomalies)

        print(f"✓ {len(anomalies)} anomalous events added")


def main():
    """Main data generation workflow."""
    print("=" * 60)
    print("eSSL Card Reader Data Generator")
    print("=" * 60)

    # Connect to database
    print(f"\nConnecting to MySQL at {MYSQL_HOST}:{MYSQL_PORT}...")

    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        cursor = conn.cursor()
        print("✓ Connected to database")
    except mysql.connector.Error as e:
        print(f"✗ Failed to connect: {e}")
        print("\nMake sure the MySQL container is running:")
        print("  docker-compose -f docker-compose.simulators.yml up -d essl-mysql")
        return

    # Generate users
    print("\nGenerating user profiles...")
    users = generate_users()
    print(f"✓ Generated {len(users)} user profiles:")
    print(f"  - Students: {NUM_STUDENTS}")
    print(f"  - Faculty: {NUM_FACULTY}")
    print(f"  - Staff: {NUM_STAFF}")
    print(f"  - Visitors: {NUM_VISITORS}")

    # Insert users
    insert_users(cursor, users)
    conn.commit()

    # Generate events
    start_date = datetime.now() - timedelta(days=DAYS_TO_GENERATE)
    total_events = generate_and_insert_events(cursor, users, start_date)
    conn.commit()

    # Add anomalies
    add_anomalies(cursor, users, start_date)
    conn.commit()

    # Statistics
    print("\n" + "=" * 60)
    print("Data Generation Complete!")
    print("=" * 60)
    print(f"Total Users: {len(users)}")
    print(f"Total Events: {total_events:,}")
    print(f"Date Range: {start_date.date()} to {datetime.now().date()}")
    print(f"Average Events/Day: {total_events // DAYS_TO_GENERATE:,}")
    print("\nYou can now test the eSSL connector with:")
    print("  ESSL_ENABLED=true")
    print("  ESSL_DB_HOST=localhost")
    print("  ESSL_DB_PORT=3307")
    print("  ESSL_DB_USER=root")
    print("  ESSL_DB_PASSWORD=essl_password")
    print("  ESSL_DB_NAME=essl_db")
    print("=" * 60)

    cursor.close()
    conn.close()


if __name__ == '__main__':
    main()
