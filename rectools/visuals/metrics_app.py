#  Copyright 2024 MTS (Mobile Telesystems)
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import typing as tp
from functools import lru_cache

import ipywidgets as widgets
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from IPython.display import display

from rectools import Columns

WIDGET_WIDTH = 800
WIDGET_HEIGHT = 500
TOP_CHART_MARGIN = 20
DEFAULT_LEGEND_TITLE = "model name"


class MetricsApp:
    """
    Jupyter widgets app for metric visualization and comparison.
    Do not create instances of this class directly. Use `MetricsApp.construct` method instead.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        metric_names: tp.List[str],
        meta_names: tp.List[str],
        show_legend: bool = True,
        auto_display: bool = True,
        scatter_kwargs: tp.Optional[tp.Dict[str, tp.Any]] = None,
    ):
        self.data = data
        self.metric_names = metric_names
        self.meta_names = meta_names
        self.show_legend = show_legend
        self.auto_display = auto_display
        self.scatter_kwargs = scatter_kwargs if scatter_kwargs is not None else {}
        self.fig = go.Figure()

        if self.auto_display:
            self.display()

    @classmethod
    def construct(
        cls,
        models_metrics: pd.DataFrame,
        models_metadata: tp.Optional[pd.DataFrame] = None,
        show_legend: bool = True,
        auto_display: bool = True,
        scatter_kwargs: tp.Optional[tp.Dict[str, tp.Any]] = None,
    ) -> "MetricsApp":
        r"""
        Construct interactive widget for metric-to-metric trade-off analysis.

        Parameters
        ----------
        models_metrics : pd.DataFrame
            A pandas DataFrame containing metrics for visualization. Required columns:
                - `Columns.Models` - model names
                - `Columns.Split` - fold number
                - Any other numeric columns which represent metric values
        models_metadata: tp.Optional[pd.DataFrame], optional, default None
            An optional pandas DataFrame containing any models metadata (hyperparameters, training info, etc.).
            Used for alternative ways of coloring scatterplot points.
            Required columns:
                - `Columns.Models` - model names
                - Any other columns with additional information
        show_legend : bool, default True
            Specifies whether to display the chart legend.
        auto_display : bool, default True
            Automatically displays the widgets immediately after initialization.
        scatter_kwargs : tp.Optional[tp.Dict[str, tp.Any]], optional, default None
            Additional arguments from `plotly.express.scatter`

        Returns
        -------
        MetricsApp
            An instance of `MetricsApp`, providing interactive Jupyter widget for metric visualization.

        Examples
        --------
        Create interactive widget

        >>> metrics_df = pd.DataFrame(
        ...    {
        ...        Columns.Model: ["Model1", "Model2", "Model1", "Model2", "Model1", "Model2"],
        ...        Columns.Split: [0, 0, 1, 1, 2, 2],
        ...        "prec@10": [0.031, 0.025, 0.027, 0.21, 0.031, 0.033],
        ...        "recall@10": [0.041, 0.045, 0.055, 0.08, 0.036, 0.021],
        ...        "novelty@10": [2.6, 11.3, 4.3, 9.8, 3.3, 11.2],
        ...    })
        >>> # Optional metainfo about models
        >>> metadata_df = pd.DataFrame(
        ...    {
        ...        Columns.Model: ["Model1", "Model2"],
        ...        "factors": [64, 32],
        ...        "regularization": [0.05, 0.05],
        ...        "alpha": [2.0, 0.5],
        ...    })
        >>> app = MetricsApp.construct(
        ...    models_metrics=metrics_df,
        ...    models_metadata=metadata_df,
        ...    show_legend=True,
        ...    auto_display=False,
        ...    scatter_kwargs={"width": 800, "height": 600})

        Get plotly chart from the current widget state

        >>> fig = app.fig
        >>> fig = fig.update_layout(title="Metrics comparison")
        """
        cls._validate_models_metrics_base(models_metrics)
        cls._validate_models_metrics_split(models_metrics)
        cls._validate_models_metrics_names(models_metrics)
        if models_metadata is None:
            models_metadata = models_metrics[Columns.Model].drop_duplicates().to_frame()
        cls._validate_models_metadata(models_metadata)

        merged_data = models_metrics.merge(models_metadata, on=Columns.Model, how="left")
        merged_data[Columns.Model] = merged_data[Columns.Model].str.replace(" ", "_")

        metric_names = [col for col in models_metrics.columns if col not in {Columns.Split, Columns.Model}]
        meta_names = [col for col in models_metadata.columns if col != Columns.Model]

        return cls(merged_data, metric_names, meta_names, show_legend, auto_display, scatter_kwargs)

    @property
    @lru_cache
    def model_names(self) -> tp.List[str]:
        """Sorted list of model names from `models_metrics`."""
        return sorted(self.data[Columns.Model].unique())

    @property
    @lru_cache
    def fold_ids(self) -> tp.Optional[tp.List[int]]:
        """Sorted list of fold identifiers from the `models_metrics`."""
        if Columns.Split in self.data.columns:
            return sorted(self.data[Columns.Split].unique())
        return None

    @staticmethod
    def _validate_models_metrics_base(models_metrics: pd.DataFrame) -> None:
        if not isinstance(models_metrics, pd.DataFrame):
            raise ValueError("Incorrect input type. `metrics_data` should be a DataFrame")
        if Columns.Model not in models_metrics.columns:
            raise KeyError("Missing `Model` column in `metrics_data` DataFrame")
        if len([item for item in models_metrics.columns if item not in {Columns.Model, Columns.Split}]) < 1:
            raise KeyError("`metrics_data` DataFrame assumed to have at least one metric column")
        if models_metrics.isnull().values.any():
            raise ValueError("Found NaN values in `metrics_data`")

    @staticmethod
    def _validate_models_metrics_split(models_metrics: pd.DataFrame) -> None:
        # Validate that each model have same folds
        if Columns.Split not in models_metrics.columns:
            return
        grouped = models_metrics.groupby(Columns.Model)
        # get the first group's fold counts and fold names for reference
        ref_group = grouped.get_group(next(iter(grouped.groups.keys())))
        ref_fold_count = ref_group[Columns.Split].nunique()
        ref_fold_names = set(ref_group[Columns.Split].unique())

        for model, group in grouped:
            if group["i_split"].nunique() != ref_fold_count:
                raise ValueError(f"{model} does not have the expected fold amount")
            if set(group["i_split"].unique()) != ref_fold_names:
                raise ValueError(f"{model} does not have the expected fold names")

    @staticmethod
    def _validate_models_metrics_names(models_metrics: pd.DataFrame) -> None:
        # Validate that all Models names are unique
        if Columns.Split in models_metrics.columns:
            models_metrics[Columns.Model] = models_metrics[Columns.Model].astype(str).str.replace(" ", "_")
            models_names_comb = models_metrics[Columns.Model] + models_metrics[Columns.Split].astype(str)
            if models_names_comb.nunique() != len(models_names_comb):
                raise ValueError("Each `Model` value in the `metrics_data` DataFrame must be unique")
        else:
            models_metrics[Columns.Model] = models_metrics[Columns.Model].astype(str).str.replace(" ", "_")
            if models_metrics[Columns.Model].nunique() != len(models_metrics[Columns.Model]):
                raise ValueError("Each `Model` value in the `metrics_data` DataFrame must be unique")

    @staticmethod
    def _validate_models_metadata(models_metadata: pd.DataFrame) -> None:
        if not isinstance(models_metadata, pd.DataFrame):
            raise ValueError("Incorrect input type. `models_metadata` should be a DataFrame")
        if Columns.Model not in models_metadata.columns:
            raise KeyError("Missing `Model`` column in `models_metadata` DataFrame")
        if models_metadata[Columns.Model].nunique() != len(models_metadata):
            raise ValueError("`Model` values of `models_metadata` should be unique`")
        if models_metadata[Columns.Model].isnull().any():
            raise ValueError("Found NaN values in `Model` column")

    @lru_cache
    def _make_chart_data_fold(self, fold_number: int) -> pd.DataFrame:
        return self.data[self.data[Columns.Split] == fold_number].reset_index(drop=True)

    @lru_cache
    def _make_chart_data_avg(self) -> pd.DataFrame:
        metric_data_columns = [Columns.Model] + self.metric_names
        meta_data_columns = [Columns.Model] + self.meta_names
        # separate metric data because meta data could contain strings
        metrics_data = self.data[metric_data_columns].groupby([Columns.Model], sort=False).mean().reset_index()
        meta_data = self.data[meta_data_columns].drop_duplicates()
        return metrics_data.merge(meta_data, on=Columns.Model, how="left").reset_index(drop=True)

    def _create_chart(
        self,
        data: pd.DataFrame,
        metric_x: str,
        metric_y: str,
        color: str,
        legend_title: str,
    ) -> go.Figure:
        scatter_kwargs = {
            "width": WIDGET_WIDTH,
            "height": WIDGET_HEIGHT,
        }
        scatter_kwargs.update(self.scatter_kwargs)

        data = data.sort_values(by=color, ascending=False)
        data[color] = data[color].astype(str)  # to treat colors values as categorical

        fig = px.scatter(
            data,
            x=metric_x,
            y=metric_y,
            color=color,
            symbol=Columns.Model,
            **scatter_kwargs,
        )
        layout_params = {
            "margin": {"t": TOP_CHART_MARGIN},
            "legend_title": legend_title,
            "showlegend": self.show_legend,
        }
        fig.update_layout(layout_params)
        return fig

    def _update_chart(
        self,
        fig_widget: go.FigureWidget,
        metric_x: widgets.Dropdown,
        metric_y: widgets.Dropdown,
        use_avg: widgets.Checkbox,
        fold_i: widgets.Dropdown,
        meta_feature: widgets.Dropdown,
        use_meta: widgets.Checkbox,
    ) -> None:  # pragma: no cover
        chart_data = self._create_chart_data(use_avg, fold_i)
        color_clmn = meta_feature.value if use_meta.value else Columns.Model

        # Save dots symbols from the previous widget state
        # `split(" ", 1)[-1]` removed metainfo from trace name. Thus we guarantee to map with traces from previous state
        trace_name2symbol = {trace.name.split(" ", 1)[-1]: trace.marker.symbol for trace in self.fig.data}
        legend_title = f"{meta_feature.value}, {DEFAULT_LEGEND_TITLE}" if use_meta.value else DEFAULT_LEGEND_TITLE
        self.fig = self._create_chart(chart_data, metric_x.value, metric_y.value, color_clmn, legend_title)

        for trace in self.fig.data:
            trace_name = trace.name.split(" ", 1)[-1]
            trace.marker.symbol = trace_name2symbol[trace_name]

        nometa_trace_name2idx = {trace.name.split(" ", 1)[-1]: idx for idx, trace in enumerate(self.fig.data)}

        with fig_widget.batch_update():
            for trace in self.fig.data:
                trace_name = trace.name.split(" ", 1)[1] if use_meta.value else trace.name
                idx = nometa_trace_name2idx[trace_name]
                fig_widget.data[idx].x = trace.x
                fig_widget.data[idx].y = trace.y
                fig_widget.data[idx].marker.color = trace.marker.color
                fig_widget.data[idx].marker.symbol = trace.marker.symbol
                fig_widget.data[idx].text = trace.text
                fig_widget.data[idx].name = trace.name
                fig_widget.data[idx].legendgroup = trace.legendgroup
                fig_widget.data[idx].hoverinfo = trace.hoverinfo
                fig_widget.data[idx].hovertemplate = trace.hovertemplate

        fig_widget.layout.update(self.fig.layout)
        self.fig.layout.margin = None  # keep separate chart non-truncated

    def _update_fold_visibility(self, use_avg: widgets.Checkbox, fold_i: widgets.Dropdown) -> None:
        fold_i.layout.visibility = "hidden" if use_avg.value else "visible"

    def _update_meta_visibility(self, use_meta: widgets.Checkbox, meta_feature: widgets.Dropdown) -> None:
        meta_feature.layout.visibility = "hidden" if not use_meta.value else "visible"

    def _create_chart_data(self, use_avg: widgets.Checkbox, fold_i: widgets.Dropdown) -> pd.DataFrame:
        if use_avg.value or fold_i.value is None:
            return self._make_chart_data_avg()
        return self._make_chart_data_fold(fold_i.value)

    def display(self) -> None:
        """Display MetricsApp widget"""
        metric_x = widgets.Dropdown(description="Metric X:", value=self.metric_names[0], options=self.metric_names)
        metric_y = widgets.Dropdown(description="Metric Y:", value=self.metric_names[-1], options=self.metric_names)
        use_avg = widgets.Checkbox(description="Average folds", value=True)
        fold_i = widgets.Dropdown(
            description="Fold number:",
            value=self.fold_ids[0] if self.fold_ids is not None else -1,
            options=self.fold_ids if self.fold_ids is not None else [-1],
        )
        use_meta = widgets.Checkbox(description="Use metadata", value=False)
        meta_feature = widgets.Dropdown(
            description="Color by:",
            value=self.meta_names[0] if self.meta_names else None,
            options=self.meta_names,
        )

        # Initialize go.FigureWidget initial chart state
        chart_data = self._create_chart_data(use_avg, fold_i)
        legend_title = f"{meta_feature.value}, {DEFAULT_LEGEND_TITLE}" if use_meta.value else DEFAULT_LEGEND_TITLE
        self.fig = self._create_chart(chart_data, metric_x.value, metric_y.value, Columns.Model, legend_title)
        fig_widget = go.FigureWidget(data=self.fig.data, layout=self.fig.layout)

        def update(event: tp.Callable[..., tp.Any]) -> None:  # pragma: no cover
            self._update_chart(fig_widget, metric_x, metric_y, use_avg, fold_i, meta_feature, use_meta)
            self._update_fold_visibility(use_avg, fold_i)
            self._update_meta_visibility(use_meta, meta_feature)

        metric_x.observe(update, "value")
        metric_y.observe(update, "value")
        use_avg.observe(update, "value")
        fold_i.observe(update, "value")
        use_meta.observe(update, "value")
        meta_feature.observe(update, "value")

        tab = widgets.Tab()

        metrics_vbox = widgets.VBox([widgets.HBox([metric_x, metric_y])])

        if self.meta_names:
            metadata_vbox = widgets.VBox([widgets.HBox([use_meta, meta_feature])])
            if self.fold_ids:
                metrics_vbox = widgets.VBox([widgets.HBox([use_avg, fold_i]), widgets.HBox([metric_x, metric_y])])
            tab.children = [metrics_vbox, metadata_vbox]
            tab.set_title(0, "Metrics")
            tab.set_title(1, "Metadata")
        else:
            if self.fold_ids:
                metrics_vbox = widgets.VBox([widgets.HBox([use_avg, fold_i]), widgets.HBox([metric_x, metric_y])])
            tab.children = [metrics_vbox]
            tab.set_title(0, "Metrics")

        display(widgets.VBox([tab, fig_widget]))

        self._update_fold_visibility(use_avg, fold_i)
        self._update_meta_visibility(use_meta, meta_feature)
        self._update_chart(fig_widget, metric_x, metric_y, use_avg, fold_i, meta_feature, use_meta)
