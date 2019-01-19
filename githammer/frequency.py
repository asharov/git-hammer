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

from enum import Enum

from dateutil.relativedelta import relativedelta


class Frequency(Enum):
    daily = 1
    weekly = 2
    monthly = 3
    yearly = 4

    def next_instance(self, dt):
        if self is Frequency.daily:
            return dt + relativedelta(days=1)
        elif self is Frequency.weekly:
            return dt + relativedelta(weeks=1)
        elif self is Frequency.monthly:
            return dt + relativedelta(months=1)
        elif self is Frequency.yearly:
            return dt + relativedelta(years=1)
