import re

from taco.response_generators.taco_rp import helpers


class WikiHowTask(helpers.Choice):
    default_views_str = "N/A"

    def __init__(self, raw_wikihow_task):
        self.item = raw_wikihow_task["_source"]
        self.has_parts = self.item["hasParts"]
        self.title = self.item["articleTitle"]
        self.name = _strip_howto(self.title)
        self.views = self.item["views"]

        self.rating = _get_rating(self.item)

        if len(self.item["methods"]) != len(self.item["methodsNames"]):
            helpers.logic_exception(
                f"Wikihow Task {self.title} does not have the same number of methods and method names: {len(self.item['methods'])} and {len(self.item['methodsNames'])}, respectively."
            )

        # Methods
        method_names = _check_method_key(self.item, "methodsNames")
        if not method_names:
            method_names = [None for _ in self.item["methods"]]

        method_images = _check_method_key(self.item, "methodsImages")
        if not method_images:
            method_images = [list() for _ in self.item["methods"]]

        method_headlines = _check_method_key(self.item, "methodsHeadlines")
        if not method_headlines:
            method_headlines = [None for method in self.item["methods"]]

        self.methods = [
            Method(method, name, images, headlines)
            for method, name, images, headlines in zip(
                self.item["methods"],
                method_names,
                method_images,
                method_headlines,
            )
        ]
        self.all_steps = [len(method) for method in self.methods]

        self.steps = 1
        if self.all_steps:
            self.steps = self.all_steps[0]

        self.img_url = None
        for img_list in reversed(self.item["methodsImages"]):
            if img_list:
                self.img_url = img_list[-1]
                break

        self.has_summary = self.item["hasSummary"]
        self.url = self.item["articleUrl"]

    @property
    def summary(self):
        return _get_short_version(self)

    @property
    def stars(self):
        if self.rating is None:
            return None
        return f"{self.rating:.2g}"

    def rating_text(self):
        if self.views:
            return f"({helpers.short_number(self.views)} {helpers.simple_plural(self.views, 'view')})"

        return ""

    def __repr__(self):
        return f"<WikihowTask methods={self.methods}>"


def _check_method_key(item, key):
    if key in item and len(item["methods"]) == len(item[key]):
        return item[key]

    return None


class Method:
    def __init__(self, steps, name, images, headlines=None):
        self.steps = [re.sub(r"\(.*?\)", "", step) for step in steps]
        self.name = name
        self.images = images
        self.headlines = headlines

    def __repr__(self):
        return f"<Method name={self.name} steps={len(self.steps)} images={len(self.images)}>"

    def __len__(self):
        return len(self.steps)


def _strip_howto(label):
    """
    Removes "How to " from the start of a string. If it's not at the start, doesn't remove anything.
    """
    if label.lower()[:6] == "how to":
        label = label[6:]

    # Removes a leading space, if any.
    return label.lstrip()


def _get_rating(wikihow_item):
    """
    None if there is no rating. Otherwise a decimal rating out of five.
    """
    if "rating" not in wikihow_item:
        return 0.0

    if wikihow_item["rating"] < 0:
        return 0.0

    return wikihow_item["rating"] / 20


def _remove_sources(summary):
    """
    Sources are normally a [1] followed by some text over multiple lines that ends with "Go to source".
    """

    fixed = re.sub(r"\[\d+?\].+? source", "", summary, flags=re.DOTALL)

    if re.search(r"\[\d+?\]", fixed):
        print(fixed)

    return fixed


def _get_short_version(wikihow_task):
    if wikihow_task.item["hasSummary"]:
        summary = wikihow_task.item["summaryText"]
        # Remove multiple consecutive newlines
        summary = re.sub("\n+", "\n", summary)

        # Remove source footnootes
        summary = _remove_sources(summary)

        # Change newlines to line breaks
        summary = summary.replace("\n", "<br/>")

        return summary

    short_ver = ""
    for i, method in enumerate(wikihow_task.methods):
        method_number = i + 1
        if wikihow_task.item["hasParts"]:
            short_ver += f"Part {method_number}: {method.name} <br>"
        else:
            short_ver += f"Method {method_number}: {method.name} <br>"

    return short_ver


def query_to_tasks(query_result):
    """
    Converts a query result to a list of WikiHowTask.
    """
    return [WikiHowTask(item) for item in query_result]
