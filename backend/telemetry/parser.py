from pymavlink import mavutil
import pandas as pd
from typing import Dict, List, Any
import numpy as np

class TelemetryParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.supported_messages = [
            'ATTITUDE', 'GLOBAL_POSITION_INT', 'VFR_HUD', 
            'SYS_STATUS', 'STATUSTEXT', 'RC_CHANNELS',
            'GPS_RAW_INT', 'BATTERY_STATUS', 'EKF_STATUS_REPORT'
        ]
        
    def parse(self) -> Dict[str, pd.DataFrame]:
        """Parse MAVLink log file and return structured data."""
        mlog = mavutil.mavlink_connection(self.file_path)
        
        # Initialize data structures for each message type
        data: Dict[str, List[Dict[str, Any]]] = {msg: [] for msg in self.supported_messages}
        
        # Read all messages
        while True:
            try:
                msg = mlog.recv_match()
                if msg is None:
                    break
                
                msg_type = msg.get_type()
                if msg_type in self.supported_messages:
                    # Convert message to dictionary and add timestamp
                    msg_dict = msg.to_dict()
                    msg_dict['timestamp'] = msg._timestamp
                    data[msg_type].append(msg_dict)
                    
            except Exception as e:
                print(f"Error parsing message: {e}")
                continue
        
        # Convert to DataFrames
        parsed_data = {}
        for msg_type, messages in data.items():
            if messages:  # Only create DataFrame if we have data
                df = pd.DataFrame(messages)
                # Convert timestamp to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                parsed_data[msg_type] = df
        
        return parsed_data
    
    def extract_flight_stats(self, data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Extract basic flight statistics from parsed data."""
        stats = {}
        
        if 'GLOBAL_POSITION_INT' in data:
            pos_df = data['GLOBAL_POSITION_INT']
            stats['max_altitude'] = pos_df['relative_alt'].max() / 1000.0  # Convert mm to m
            stats['min_altitude'] = pos_df['relative_alt'].min() / 1000.0
            stats['flight_distance'] = self._calculate_total_distance(pos_df)
        
        if 'GPS_RAW_INT' in data:
            gps_df = data['GPS_RAW_INT']
            stats['gps_signal_losses'] = self._count_gps_losses(gps_df)
        
        if 'BATTERY_STATUS' in data:
            bat_df = data['BATTERY_STATUS']
            if 'temperature' in bat_df.columns:
                stats['max_battery_temp'] = bat_df['temperature'].max()
        
        # Calculate total flight time
        all_timestamps = []
        for df in data.values():
            if not df.empty and 'timestamp' in df.columns:
                all_timestamps.extend(df['timestamp'].tolist())
        
        if all_timestamps:
            stats['flight_duration'] = (max(all_timestamps) - min(all_timestamps)).total_seconds()
        
        return stats
    
    def _calculate_total_distance(self, pos_df: pd.DataFrame) -> float:
        """Calculate total flight distance in meters."""
        if pos_df.empty or len(pos_df) < 2:
            return 0.0
            
        def haversine_distance(lat1, lon1, lat2, lon2):
            R = 6371000  # Earth radius in meters
            
            lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
            c = 2 * np.arcsin(np.sqrt(a))
            
            return R * c
        
        total_distance = 0
        prev_lat = pos_df.iloc[0]['lat'] / 1e7  # Convert from degE7 to degrees
        prev_lon = pos_df.iloc[0]['lon'] / 1e7
        
        for _, row in pos_df.iloc[1:].iterrows():
            lat = row['lat'] / 1e7
            lon = row['lon'] / 1e7
            total_distance += haversine_distance(prev_lat, prev_lon, lat, lon)
            prev_lat, prev_lon = lat, lon
            
        return total_distance
    
    def _count_gps_losses(self, gps_df: pd.DataFrame) -> int:
        """Count number of GPS signal losses."""
        if 'fix_type' not in gps_df.columns:
            return 0
            
        # Consider fix_type < 2 as GPS loss (no fix or 1D fix)
        losses = 0
        prev_fix = True
        
        for fix in gps_df['fix_type'] >= 2:
            if prev_fix and not fix:
                losses += 1
            prev_fix = fix
            
        return losses 