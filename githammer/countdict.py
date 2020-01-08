# Copyright 2019 Jaakko Kangasharju
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


def normalize_count_dict(count_dict):
    return {key: value for key, value in count_dict.items() if value != 0}


def subtract_count_dict(base_dict, dict_to_subtract):
    result_dict = base_dict.copy()
    for key, value in dict_to_subtract.items():
        result_dict[key] = result_dict.get(key, 0) - value
    return normalize_count_dict(result_dict)


def add_count_dict(base_dict, dict_to_add):
    result_dict = base_dict.copy()
    for key, value in dict_to_add.items():
        result_dict[key] = result_dict.get(key, 0) + value
    return normalize_count_dict(result_dict)
