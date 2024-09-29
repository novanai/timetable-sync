import arc

from timetable import api as api_
from timetable import models

CATEGORY_TYPES: dict[str, models.CategoryType] = {
    "course": models.CategoryType.PROGRAMMES_OF_STUDY,
    "module": models.CategoryType.MODULES,
    "location": models.CategoryType.LOCATIONS,
}


async def search_categories(
    data: arc.AutocompleteData[arc.GatewayClient, str],
) -> dict[str, str]:
    api = data.client.get_type_dependency(api_.API)

    if data.focused_option and data.focused_value:
        categories = await api.get_category(
            CATEGORY_TYPES[data.focused_option.name],
            query=data.focused_value,
            count=10,
        )
        if categories is None:
            return {}

        return {item.name: item.identity for item in categories.items}

    return {}
