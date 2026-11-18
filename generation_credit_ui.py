"""Temporary credit notices shown alongside generation progress."""

from contextlib import contextmanager

import streamlit as st


def generation_credit_message(engine_name, amount, balance, *, pending=False):
    charge = "will be deducted on success" if pending else "deducted"
    balance_label = "current balance" if pending else "remaining"
    return (
        f"{engine_name}: {amount:,} credits {charge} · "
        f"{balance:,.2f} credits {balance_label}."
    )


@contextmanager
def generation_credit_progress(engine_name, amount, *, pending=False):
    placeholder = st.empty()
    try:
        placeholder.info(
            generation_credit_message(
                engine_name, amount, st.session_state["user_credits"], pending=pending
            )
        )
        yield placeholder
    finally:
        placeholder.empty()
