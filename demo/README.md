# Ex2Bundle Demo (Section 6 — User Study)

The interactive Flask + JavaScript application used in the user study (paper
Section 6, Figures 7 & 15). Slider UI is implemented in
`server_code/flask_code/web/static/scripts_sudocu.js`; the Python backend
exposes `/learn` and `/refine` endpoints that drive the
`Ex2BundleSlider` model.

This is the **deployed** version with `ConflictRefiner` enabled — same
algorithm as `models/ex2bundle.py`, plus the slider relaxation from
`models/ex2bundle_slider.py`.

## Layout

```
demo/
├── server_code/
│   ├── flask_code/
│   │   ├── app.py                # Flask entry point
│   │   ├── requirements.txt
│   │   └── web/
│   │       ├── static/           # JS (slider UI), CSS, images, tutorial video
│   │       └── templates/        # HTML pages (consent, tutorials, tasks, post-study)
│   ├── Models/                   # Deployed copy of SuDocu_*_RELAX models
│   └── utils/
└── demo_site/                    # Older standalone demo (not used in user study)
```

## Run locally

### 1. Install Flask backend deps
```bash
cd demo/server_code/flask_code
pip install -r requirements.txt
# Plus the Ex2Bundle deps:
pip install -r ../../../requirements.txt
```

### 2. Symlink the shared data into the Flask working directory
The Flask app expects `data/data_ctm.csv` and `data/StateDocuments/...`
relative to its CWD. We share these with the rest of the repo via:

```bash
cd demo/server_code/flask_code
ln -s ../../../data/shared_docs data
ln -s ../../../data/data_ctm.csv data_ctm.csv
```

### 3. Launch
```bash
cd demo/server_code
python -m flask_code.app
```

Visit http://localhost:5000.

## Notes

- The `User_Study_Data/` folder used for logging participant interactions is
  **not** included — it was created at run-time during the actual study.
  If you re-deploy, point `logging_data_path` in `app.py` somewhere writable.
- The 11 MB `SuDocu.mp4` tutorial video is preserved (it's referenced by the
  tutorial pages). Strip it if you only need the algorithm demo.
- This code corresponds to the deployed slider variant. For
  experiment-mode (no-slider) Ex2Bundle, use `models/ex2bundle.py` and the
  scripts under `experiments/`.
