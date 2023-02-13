

def test_delay_draw(qtbot, example, cycle_tabs):
    # run example
    ui = example.example_delay_draw()
    ui.show()

    # register ui
    qtbot.addWidget(ui)

    # test
    cycle_tabs(qtbot, ui)
