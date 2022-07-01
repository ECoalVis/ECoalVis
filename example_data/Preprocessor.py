#!/usr/bin/env python
# coding: utf-8

# In[245]:


import pandas as pd
import numpy as np
import json
# read data
sensor_data = pd.read_csv("./example_data.csv") 
config = pd.read_csv("./example_config.csv")
pipeline = pd.read_csv("./example_pipeline.csv")

component_link_weight = 1.0
unit_link_weight = 1.0
sensor_link_weight_threshold = 0.8

sensor_name_id_map = {}
for i in range(len(config)):
    sensor_name_id_map[config.loc[i,"chn"]] = config.loc[i,"index"]


# In[246]:


# start calculating links
link_cols = ["link_id","link_type","src_id","dst_id","weight"]
links=pd.DataFrame(columns=link_cols)
link_cnt = 0

## links between components
for i in range(len(pipeline)):
    if pipeline.loc[i,"link_type"] == 0:
        links.loc[len(links)] = [link_cnt, 0, pipeline.loc[i,"src_id"],pipeline.loc[i,"dst_id"], component_link_weight]
        link_cnt += 1


# In[247]:


## links between units
for i in range(len(pipeline)):
    if pipeline.loc[i,"link_type"] == 1:
        links.loc[len(links)] = [link_cnt, 1, pipeline.loc[i,"src_id"],pipeline.loc[i,"dst_id"], unit_link_weight]
        link_cnt += 1


# In[248]:


## links between sensors
corr_values = sensor_data.corr().abs()
sensor_cols = sensor_data.columns.tolist()

for i in range(1,len(corr_values)):
    # skip index column
    for j in range(i + 1, len(corr_values)):
        if corr_values.iloc[i,j] > sensor_link_weight_threshold:
            links.loc[len(links)] = [link_cnt, 2, sensor_name_id_map[sensor_cols[i]], sensor_name_id_map[sensor_cols[j]], corr_values.iloc[i,j]]
            link_cnt += 1


# In[249]:


pd.DataFrame(links).to_csv('./example_links.csv');


# In[280]:


def is_up_convex(l,r,sensor):
    st = l
    ed = r
    fir = st + (ed - st) // 3
    sec = st + (ed - st) * 2 // 3
    test_fir = sensor[l]+(sensor[r] - sensor[l]) / 3
    test_sec = sensor[l]+(sensor[r] - sensor[l]) * 2 / 3

    if test_fir >= sensor[fir] and test_sec >= sensor[sec]:
        return False
    elif test_fir <= sensor[fir] and test_sec <= sensor[sec]:
        return True
    elif test_fir >= sensor[fir] and test_sec <= sensor[sec]:
        return False
    else:
        return True


# In[315]:


def find_first_max_up(l,r,data,eps):
    ans = r
    while l <= r:
        fir = l + (r - l) // 3
        sec = l + (r - l) * 2 // 3
        if l == r - 1 and fir == sec:
            sec = fir + 1
        if data[sec] - data[fir] < eps: # <=
            ans = sec
            r = sec - 1
        else:
            l = fir + 1
    return ans

def find_last_min_down(l,r,data,eps):
    ans = l
    while l <= r:
        fir = l + (r - l) // 3
        sec = l + (r - l) * 2 // 3
        if l == r - 1 and fir == sec:
            sec = fir + 1
        if data[fir] - data[sec] > -eps: # >=
            ans = sec
            l = fir + 1
        else:
            r = sec - 1
    return ans

def find_first_min_down(l,r,data,eps):
    ans = r
    while l <= r:
        fir = l + (r - l) // 3
        sec = l + (r - l) * 2 // 3
        if l == r - 1 and fir == sec:
            sec = fir + 1
        if data[sec] - data[fir] > -eps: # >=
            r = sec - 1
            ans = sec
        else:
            l = fir + 1
    return ans

def find_last_max_up(l,r,data,eps):
    ans = l
    while l <= r:
        fir = l + (r - l) // 3
        sec = l + (r - l) * 2 // 3
        if l == r - 1 and fir == sec:
            sec = fir + 1
        if data[fir] - data[sec] < eps: #<= 
            l = fir + 1
            ans = sec
        else:
            r = sec - 1
    return ans


# In[316]:


def discrete(sensor, window_size = 20, eps_jitter = 1e-4):
    st = 0
    ed = st + window_size
    length = len(sensor)
    jitter_par = (max(sensor) - min(sensor))*eps_jitter
    event = {}
    cnt = 0
    while st < length-1 and ed < length:
        event_end, event_start = 0, 0
        if is_up_convex(st,ed,sensor):
            event_end = find_first_max_up(st, ed, sensor, jitter_par)
            event_start = find_last_min_down(st, event_end, sensor, jitter_par)
            if event_end <= st:
                event_end = find_last_max_up(st, ed, sensor, jitter_par)
                event_start = find_first_min_down(st, event_end, sensor, jitter_par)
        else:
            event_end = find_first_min_down(st, ed, sensor, jitter_par)
            event_start = find_last_max_up(st, event_end, sensor, jitter_par)
            if event_end <= st:
                event_end = find_last_min_down(st, ed, sensor, jitter_par)
                event_start = find_first_max_up(st, event_end, sensor, jitter_par)
        if abs(sensor[event_end] - sensor[event_start]) > jitter_par:
            event[str(cnt)] = {
                "start":event_start,
                "end":event_end,
                "value":sensor[event_end] - sensor[event_start]
                }
            cnt += 1
            st = event_end
            ed = st + window_size
        else:    
            if event_end == st and event_start == st:
                st = event_end + 1
            else:
                st = event_end
            ed = st + window_size
        if ed > length:
            ed = length - 1
    return event


# In[317]:


# start discretization
## 
all_events = {}
for i in range(0,len(sensor_cols)):
    # skip index column
    # skip timestamp column
    if sensor_cols[i] == "index" or sensor_cols[i] == "Timestamp":
        continue
    sensor = sensor_data.loc[:,sensor_cols[i]].values.tolist()
    event = discrete(sensor,10)
    all_events[sensor_cols[i]] = event
    
with open("example_events.json","w") as f:
    f.write(json.dumps((all_events),indent=4))


