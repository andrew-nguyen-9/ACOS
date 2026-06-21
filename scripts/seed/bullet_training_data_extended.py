"""Master extended bullet file — 2500 entries across 5 role types."""

from scripts.seed.bullet_training_data_ext_pm import PM_BULLETS
from scripts.seed.bullet_training_data_ext_da import DA_BULLETS
from scripts.seed.bullet_training_data_ext_cons import CONS_BULLETS
from scripts.seed.bullet_training_data_ext_eng import ENG_BULLETS
from scripts.seed.bullet_training_data_ext_tpm import TPM_BULLETS

BULLET_EXAMPLES_EXTENDED = PM_BULLETS + DA_BULLETS + CONS_BULLETS + ENG_BULLETS + TPM_BULLETS

assert len(BULLET_EXAMPLES_EXTENDED) == 2500, (
    f"Expected 2500 extended bullets, got {len(BULLET_EXAMPLES_EXTENDED)}"
)
