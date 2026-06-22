from toshiba_test30_factory import draw_single_label, build_job_factory_match, DATA
img = draw_single_label(DATA)
job = build_job_factory_match(img)
with open('test30.prn', 'wb') as f:
    f.write(job)
