import streamlit as st
import pandas as pd
import plotly.express as px
from db import (
    list_trades
)
from utils.metrics import compute_metrics, equity_curve
from helpers import apply_page_config_from_file

apply_page_config_from_file(__file__)

