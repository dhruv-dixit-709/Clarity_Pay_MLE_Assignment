from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass
class ModelArtifacts:
    model_pipeline: Pipeline
    evaluation: dict[str, Any]
    scored_df: pd.DataFrame
    portfolio_summary: dict[str, float]
    coefficients_df: pd.DataFrame


def train_risk_model(feature_df: pd.DataFrame) -> ModelArtifacts:
    model_df = feature_df.copy()

    numeric_features = [
        "log_monthly_volume",
        "log_last_30d_volume",
        "log_last_30d_txn_count",
        "avg_ticket_size",
        "csv_implied_avg_ticket",
        "api_volume_to_monthly_volume_ratio",
        "api_txn_to_csv_txn_ratio",
        "avg_ticket_gap_ratio",
        "risk_flag_encoded",
        "review_age_days",
        "risk_flag_x_review_stale",
    ]
    categorical_features = ["volume_band", "region", "subregion", "merchant_sector", "registration_type"]
    boolean_features = [
        "has_registration_number",
        "is_uk",
        "review_is_stale",
        "missing_country_enrichment",
        "volume_mismatch_flag",
        "avg_ticket_mismatch_flag",
    ]
    feature_columns = numeric_features + categorical_features + boolean_features
    target_col = "high_dispute_risk"

    X = model_df[feature_columns]
    y = model_df[target_col]
    if y.nunique() < 2:
        raise ValueError("Risk model training requires at least two target classes.")

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="missing")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    boolean_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
            ("bool", boolean_transformer, boolean_features),
        ]
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("model", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )

    stratify_target = y if y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.3,
        random_state=42,
        stratify=stratify_target,
    )
    pipeline.fit(X_train, y_train)
    y_prob = pipeline.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)

    transformed_feature_names = pipeline.named_steps["preprocessor"].get_feature_names_out()
    coefficients_df = pd.DataFrame(
        {
            "feature": transformed_feature_names,
            "coefficient": pipeline.named_steps["model"].coef_[0],
        }
    )
    coefficients_df["abs_coefficient"] = coefficients_df["coefficient"].abs()
    coefficients_df = coefficients_df.sort_values("abs_coefficient", ascending=False).reset_index(drop=True)

    evaluation = {
        "roc_auc": float(roc_auc_score(y_test, y_prob)),
        "classification_report": classification_report(y_test, y_pred, zero_division=0),
        "train_positive_rate": float(y_train.mean()),
        "test_positive_rate": float(y_test.mean()),
        "model_feature_columns": feature_columns,
        "label_column": target_col,
        "training_row_count": int(len(X_train)),
        "test_row_count": int(len(X_test)),
        "top_positive_features": coefficients_df.sort_values("coefficient", ascending=False)
        .head(5)[["feature", "coefficient"]]
        .to_dict(orient="records"),
        "top_negative_features": coefficients_df.sort_values("coefficient", ascending=True)
        .head(5)[["feature", "coefficient"]]
        .to_dict(orient="records"),
    }
    if stratify_target is None:
        evaluation["split_note"] = "Performed non-stratified split because a class had fewer than two rows."

    model_df["predicted_high_risk_probability"] = pipeline.predict_proba(X)[:, 1]
    model_df["predicted_high_risk"] = (model_df["predicted_high_risk_probability"] >= 0.5).astype(int)

    # Simple loss proxy: expected loss rate * monthly volume.
    assumed_loss_rate_for_high_risk = 0.035
    model_df["expected_loss_proxy"] = (
        model_df["predicted_high_risk_probability"] * assumed_loss_rate_for_high_risk * model_df["monthly_volume"]
    )
    portfolio_summary = {
        "merchant_count": float(len(model_df)),
        "expected_high_risk_merchants": float(model_df["predicted_high_risk_probability"].sum()),
        "expected_loss_proxy_total": float(model_df["expected_loss_proxy"].sum()),
        "mean_predicted_risk_probability": float(model_df["predicted_high_risk_probability"].mean()),
    }

    return ModelArtifacts(
        model_pipeline=pipeline,
        evaluation=evaluation,
        scored_df=model_df,
        portfolio_summary=portfolio_summary,
        coefficients_df=coefficients_df,
    )
