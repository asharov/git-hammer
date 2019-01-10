def _normalize_count_dict(dict):
    return {key: value for key, value in dict.items() if value != 0}


def subtract_count_dict(base_dict, dict_to_subtract):
    result_dict = base_dict.copy()
    for key, value in dict_to_subtract.items():
        result_dict[key] = result_dict.get(key, 0) - value
    return _normalize_count_dict(result_dict)


def add_count_dict(base_dict, dict_to_add):
    result_dict = base_dict.copy()
    for key, value in dict_to_add.items():
        result_dict[key] = result_dict.get(key, 0) + value
    return _normalize_count_dict(result_dict)
