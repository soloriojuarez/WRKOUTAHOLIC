"""
inference.py
Statistical inference layer - goes past the descriptive regression slope in
analytics.py to answer "is this real, or noise?":

- trend_significance(): a 95% confidence interval and p-value on the
  progressive-overload slope (scipy.stats.linregress), instead of reporting
  a point estimate with no notion of uncertainty.
- rep_range_comparison(): a two-sample hypothesis test (Welch's t-test)
  comparing estimated 1RM between low- and high-rep sets for an exercise.

IMPORTANT caveat, stated deliberately and not glossed over: rep_range_comparison
is an OBSERVATIONAL comparison, not a randomized experiment. Rep range wasn't
randomly assigned - it's confounded with time (progressive overload means
later sessions differ from earlier ones regardless of rep range), so a
significant result here is evidence of association, not proof that rep
range *causes* the difference. A real A/B test would randomize rep range
assignment across sessions to break that confound.
"""

from scipy import stats as scipy_stats

import analytics
import db

MIN_SESSIONS_FOR_TREND_TEST = 4
CONFIDENCE_LEVEL = 0.95
SIGNIFICANCE_ALPHA = 0.05


def trend_significance(exercise_name: str) -> dict:
    """
    Fits the same best-set-per-session series as analytics.progressive_overload_trend
    but via scipy.stats.linregress, which additionally gives a p-value and
    standard error - enough to build a 95% CI on the slope and state whether
    the trend is statistically distinguishable from zero, not just its sign.
    """
    df = analytics.best_set_over_time(exercise_name)
    n = len(df)
    if n < MIN_SESSIONS_FOR_TREND_TEST:
        return {
            "significant": None,
            "message": f"Need at least {MIN_SESSIONS_FOR_TREND_TEST} sessions "
                       f"to test significance ({n} so far).",
        }

    x = range(n)
    y = df["est_1rm"].values
    result = scipy_stats.linregress(x, y)

    df_resid = n - 2
    t_crit = scipy_stats.t.ppf(1 - (1 - CONFIDENCE_LEVEL) / 2, df_resid)
    margin = t_crit * result.stderr
    ci_low, ci_high = result.slope - margin, result.slope + margin

    significant = result.pvalue < SIGNIFICANCE_ALPHA
    if significant:
        direction = "increasing" if result.slope > 0 else "decreasing"
        message = (
            f"Statistically significant {direction} trend (p={result.pvalue:.3f} < "
            f"{SIGNIFICANCE_ALPHA}): slope {result.slope:+.2f} lbs/session, "
            f"95% CI [{ci_low:+.2f}, {ci_high:+.2f}]."
        )
    else:
        message = (
            f"Not statistically significant (p={result.pvalue:.3f} >= {SIGNIFICANCE_ALPHA}): "
            f"can't distinguish this trend from no trend given only {n} sessions. "
            f"95% CI on slope [{ci_low:+.2f}, {ci_high:+.2f}] includes 0."
        )

    return {
        "significant": bool(significant),
        "slope": round(float(result.slope), 3),
        "p_value": round(float(result.pvalue), 4),
        "r_squared": round(float(result.rvalue) ** 2, 3),
        "ci_low": round(float(ci_low), 3),
        "ci_high": round(float(ci_high), 3),
        "n_sessions": n,
        "message": message,
    }


def rep_range_comparison(exercise_name: str, low_max: int = 6, high_min: int = 8) -> dict:
    """
    Welch's two-sample t-test (unequal variances assumed - more defensible
    than Student's t here since low- and high-rep sets have no reason to
    share variance) comparing estimated 1RM between sets done at <= low_max
    reps vs >= high_min reps. See module docstring for the observational
    (non-randomized) caveat.
    """
    rows = db.get_sets_by_rep_range(exercise_name)
    low = [analytics.estimated_1rm(w, r) for w, r in rows if r <= low_max]
    high = [analytics.estimated_1rm(w, r) for w, r in rows if r >= high_min]

    if len(low) < 2 or len(high) < 2:
        return {
            "significant": None,
            "message": f"Not enough sets in both rep ranges yet (low-rep n={len(low)}, "
                       f"high-rep n={len(high)}; need >= 2 in each).",
        }

    t_stat, p_value = scipy_stats.ttest_ind(low, high, equal_var=False)
    mean_low = sum(low) / len(low)
    mean_high = sum(high) / len(high)
    significant = p_value < SIGNIFICANCE_ALPHA

    higher_group = f"<={low_max}-rep" if mean_low > mean_high else f">={high_min}-rep"
    if significant:
        message = (
            f"Statistically significant difference (p={p_value:.3f}): "
            f"{higher_group} sets show higher estimated 1RM on average. "
            f"This is an observational comparison, not a randomized experiment - "
            f"rep range is confounded with training time, so this shows "
            f"association, not that rep range alone causes the difference."
        )
    else:
        message = (
            f"No statistically significant difference (p={p_value:.3f} >= {SIGNIFICANCE_ALPHA}) "
            f"between rep ranges for this exercise given the current sample."
        )

    return {
        "significant": bool(significant),
        "t_statistic": round(float(t_stat), 3),
        "p_value": round(float(p_value), 4),
        "mean_est_1rm_low_rep": round(mean_low, 1),
        "mean_est_1rm_high_rep": round(mean_high, 1),
        "n_low_rep": len(low),
        "n_high_rep": len(high),
        "message": message,
    }
