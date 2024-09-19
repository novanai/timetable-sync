import arc
from timetable import api as api_
from timetable import utils, models

CATEGORY_TYPES: dict[str, models.CategoryType] = {
    "course": models.CategoryType.PROGRAMMES_OF_STUDY,
    "module": models.CategoryType.MODULES,
}

# TODO: technically this file isn't required unless other plugins need it
async def search_categories(
    data: arc.AutocompleteData[arc.GatewayClient, str],
) -> dict[str, str]:
    api = data.client.get_type_dependency(api_.API)
    if data.focused_option and data.focused_value:
        categories = await api.get_category_results(
            CATEGORY_TYPES[data.focused_option.name], data.focused_value, 10
        )
        if categories is None:
            await utils.get_basic_category_results(api)
            return {}

        return {item.name: item.code for item in categories.items}

    return {}
