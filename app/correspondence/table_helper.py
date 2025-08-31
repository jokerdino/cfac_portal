import math


from sqlalchemy.inspection import inspect
from flask import request, url_for, render_template
from markupsafe import Markup


class Column:
    def __init__(self, header, accessor=None, formatter=None, is_html=False):
        """
        :param header: Column header label
        :param accessor: Model attribute name (string)
        :param formatter: Callable(row) -> value (overrides accessor)
        :param is_html: Whether formatter returns safe HTML
        """
        self.header = header
        self.accessor = accessor
        self.formatter = formatter
        self.is_html = is_html

    def get_value(self, row, table=None, name=None):
        # 1. If table has a render_<name> method, use it
        if table and name:
            render_method = getattr(table, f"render_{name}", None)
            if render_method:
                return render_method(row)

        # 2. Else use formatter
        if self.formatter:
            return self.formatter(row)

        # 3. Else use accessor
        if self.accessor:
            return getattr(row, self.accessor, "")

        return ""


class Table:
    def __init__(
        self,
        model_or_query,
        only=None,
        exclude=None,
        extra_columns=None,
        classes="table table-striped",
        id=None,
        paginate=True,
        per_page=10,
    ):
        self.classes = classes
        self.id = id
        self.paginate = paginate
        self.per_page = per_page
        self.page = int(request.args.get("page", 1))
        self.sort_by = request.args.get("sort")
        self.order = request.args.get("order", "asc")

        # Detect model & query
        if hasattr(model_or_query, "all") or hasattr(model_or_query, "count"):
            # SQLAlchemy Query
            self.model = model_or_query.column_descriptions[0]["entity"]
            self.query = model_or_query
        else:
            # SQLAlchemy Model
            self.model = model_or_query
            self.query = self.model.query

        # Auto-detect model columns
        mapper = inspect(self.model)
        cols = [
            (c.key, Column(c.key.capitalize().replace("_", " "), accessor=c.key))
            for c in mapper.attrs
            if hasattr(c, "columns")
        ]

        # Apply only/exclude filters
        if only:
            cols = [(k, c) for k, c in cols if k in only]
        if exclude:
            cols = [(k, c) for k, c in cols if k not in exclude]

        # Add custom columns
        self.columns = cols + (extra_columns or [])

        # Apply query sorting/pagination
        self._process_query()

    def _process_query(self):
        query = self.query

        # Sorting
        if self.sort_by and self.sort_by in [name for name, _ in self.columns]:
            col_attr = getattr(self.model, self.sort_by)
            if self.order == "desc":
                query = query.order_by(col_attr.desc())
            else:
                query = query.order_by(col_attr.asc())

        # Pagination
        if self.paginate:
            self.total = query.count()
            self.pages = math.ceil(self.total / self.per_page)
            self.data = (
                query.limit(self.per_page).offset((self.page - 1) * self.per_page).all()
            )
        else:
            self.total = query.count()
            self.pages = 1
            self.data = query.all()

    # Helpers for templates
    def sort_url(self, column, order="asc"):
        args = request.args.to_dict()
        args["sort"] = column
        args["order"] = order
        return url_for(request.endpoint, **args)

    def page_url(self, page):
        args = request.args.to_dict()
        args["page"] = page
        return url_for(request.endpoint, **args)

    def __html__(self):
        return render_template("table.html", table=self)

    @property
    def pagination(self):
        return render_template("pagination.html", table=self)

    def rows(self):
        for row in self.data:
            yield [
                (name, col.get_value(row, table=self, name=name))
                for name, col in self.columns
            ]

    # Factory method: like Django-Tables2
    @classmethod
    def from_model(cls, model, only=None, exclude=None, **kwargs):
        class ModelTable(cls):
            def __init__(self, query_or_none=None, **extra_kwargs):
                if query_or_none is None:
                    query_or_none = model
                super().__init__(
                    query_or_none,
                    only=only,
                    exclude=exclude,
                    **{**kwargs, **extra_kwargs},
                )

        ModelTable.__name__ = f"{model.__name__}Table"
        return ModelTable
