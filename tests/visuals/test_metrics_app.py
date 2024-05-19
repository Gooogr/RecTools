import typing as tp

import pandas as pd
import plotly.express as px
import pytest

from rectools import Columns
from rectools.visuals.metrics_app import MetricsApp

DF_METRICS = pd.DataFrame(
    {
        Columns.Model: ["Model1", "Model2", "Model1", "Model2", "Model1", "Model2"],
        Columns.Split: [0, 0, 1, 1, 2, 2],
        "prec@10": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        "recall": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
    }
)

DF_METRICS_EMPTY = pd.DataFrame(
    {
        Columns.Model: ["Model1", "Model2", "Model1", "Model2", "Model1", "Model2"],
        Columns.Split: [0, 0, 1, 1, 2, 2],
    }
)

DF_METRICS_NO_MODEL = pd.DataFrame(
    {
        Columns.Split: [0, 0, 1, 1, 2, 2],
        "prec@10": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        "recall": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
    }
)


class TestMetricsApp:
    @pytest.mark.parametrize("show_legend", (True, False))
    @pytest.mark.parametrize(
        "plotly_kwargs",
        [
            None,
            {"width": None, "height": None, "color_discrete_sequence": None},
            {"width": 0, "height": 0, "color_discrete_sequence": px.colors.qualitative.Plotly},
            {
                "width": 800,
                "height": 600,
                "color_discrete_sequence": ["#0d0887", "#46039f", "#7201a8", "#9c179e", "#bd3786", "#d8576b"],
            },
        ],
    )
    def test_happy_path(
        self,
        show_legend: bool,
        plotly_kwargs: tp.Optional[tp.Dict[str, tp.Any]],
    ) -> None:
        MetricsApp.construct(
            df_metrics_data=DF_METRICS,
            show_legend=show_legend,
            auto_display=False,
            plotly_kwargs=plotly_kwargs,
        )

    def test_no_metric_columns(self) -> None:
        with pytest.raises(KeyError):
            MetricsApp.construct(
                df_metrics_data=DF_METRICS_EMPTY,
            )

    def test_no_base_columns(self) -> None:
        with pytest.raises(KeyError):
            MetricsApp.construct(
                df_metrics_data=DF_METRICS_NO_MODEL,
            )
