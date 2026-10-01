import QtQuick
import QtTest
import "../../Common/functions/SpotlightCurrency.js" as Currency
import "../../Common/functions/SpotlightTemplates.js" as Templates
import "../../Common/functions/SpotlightSession.js" as Session
import "../../Common/functions/SpotlightCommands.js" as Commands
import "../../Common/functions/SpotlightToolResponse.js" as ToolResponse

TestCase {
    name: "SpotlightSession"

    function test_obsoleteToolAnswers() {
        const request = {
            generation: 2,
            instance: 1
        };
        const answer = {
            ok: true,
            error: null,
            answer: "170"
        };
        verify(ToolResponse.copyable(answer, request, true, "valid", 2, 1));
        // Editing input, returning/re-entering a tool and closing invalidate an
        // otherwise valid response even if the backend finishes afterward.
        verify(!ToolResponse.copyable(answer, request, true, "valid", 3, 1));
        verify(!ToolResponse.copyable(answer, request, true, "valid", 2, 2));
        verify(!ToolResponse.copyable(answer, request, false, "valid", 2, 1));
        verify(!ToolResponse.copyable(answer, request, true, "loading", 2, 1));
        verify(!ToolResponse.copyable({
                                          ok: false,
                                          error: {
                                              code: "timeout"
                                          },
                                          answer: "error"
                                      }, request, true, "valid", 2, 1));
    }

    function test_parentAndOverrides() {
        let state = Session.create("apps");
        state = Session.setOverride(state, "appsLayout", "grid", "list");
        state = Session.setOverride(state, "appsOrder", "smart", "name");
        state = Session.input(state, "/calc", false, "app:one");
        const tool = Session.enterTool(state, "calculator", "8/2", true);
        compare(tool.query, "8/2");
        compare(Session.route(tool, "8/2").kind, "query");
        state = Session.pop(tool);
        compare(state.mode, "apps");
        compare(state.query, "");
        compare(state.selectionId, "app:one");
        compare(Session.effective(state, "appsLayout", "list"), "grid");
        compare(Session.effective(state, "appsOrder", "name"), "smart");
        state = Session.pop(state);
        compare(Session.effective(state, "appsOrder", "name"), "name");
        compare(Session.effective(state, "appsLayout", "list"), "grid");
        state = Session.pop(state);
        compare(Session.effective(state, "appsLayout", "list"), "list");
        compare(Session.pop(state), state);
    }

    function test_boundedReplacement() {
        let state = Session.create("apps");
        for (let i = 0; i < 100; ++i)
            state = Session.setOverride(state, "appsLayout", i % 2 ? "grid" : "list", "list");
        compare(state.overrides.length, 1);
        let tool = Session.enterTool(state, "calculator", "", false);
        for (let i = 0; i < 100; ++i)
            tool = Session.enterTool(tool, i % 2 ? "time" : "currency", "", false);
        compare(Session.pop(tool).overrides.length, 1);
        verify(!Session.pop(tool).parent);
        state = Session.setOverride(state, "appsLayout", "list", "list");
        compare(state.overrides.length, 0);
    }

    function test_commandsAndLiteral() {
        const state = Session.create("search");
        compare(Session.route(state, ">calc").query, "calc");
        compare(Session.route(state, "\\/etc").kind, "literal");
        compare(Session.route(state, "\\>hello").query, ">hello");
        compare(Session.route(Session.input(state, "/app", true), "/app").kind, "query");
        verify(Commands.match("", true).every(entry => !!Commands.exact(entry.slashName)));
        verify(Commands.match("", true).every(entry => entry.kind !== "override"));
        compare(Commands.exact("search").value, "web");
        compare(Commands.exact("default").value, "search");
        compare(Commands.exact("clal"), null);
        compare(Commands.resolve("grid", "", state).error, "scope");
        compare(Commands.resolve("light", "extra", state).error, "arguments");
        compare(Commands.resolve("cal", "", state).error, "unknown");
        compare(Commands.resolve("currency", "100 USD to CNY", state).entry.id, "tool.currency");
        const commands = Session.input(Session.create("commands"), "calc", false);
        compare(Session.pop(Session.enterTool(commands, "calculator", "", false)).query, "calc");
    }

    function test_commandContextReturn() {
        let source = Session.setOverride(Session.create("apps"), "appsLayout", "grid", "list");
        source = Session.input(source, "terminal", false, "app:terminal");
        const commands = Session.enterCommands(source, "");
        compare(commands.mode, "commands");
        verify(Session.canBackspace(commands, {
                                        searchFocus: true
                                    }));
        verify(!Session.canBackspace(Session.input(commands, "calc", false), {
                                         searchFocus: true
                                     }));
        const restored = Session.pop(commands);
        compare(restored.mode, "apps");
        compare(restored.query, "terminal");
        compare(restored.selectionId, "app:terminal");
        compare(Session.effective(restored, "appsLayout", "list"), "grid");
        const tool = Session.enterTool(commands, "calculator", "1+1", false);
        compare(Session.pop(tool).mode, "commands");
        compare(Session.pop(Session.pop(tool)).mode, "apps");
        verify(!Session.switchMode(commands, "files", false).parent);
        verify(!Session.canBackspace(Session.create("commands"), {
                                         searchFocus: true
                                     }));
    }

    function test_backspaceGuards() {
        const state = Session.enterTool(Session.create("apps"), "calculator", "", false);
        const event = {
            searchFocus: true
        };
        verify(Session.canBackspace(state, event));
        for (const guard of ["selection", "preedit", "modal", "repeat"])
            verify(!Session.canBackspace(state, Object.assign({}, event, {
                                                                  [guard]: true
                                                              })));
        verify(!Session.canBackspace(state, {
                                         searchFocus: false
                                     }));
        verify(!Session.canBackspace(Session.input(state, " ", false), event));
        verify(!Session.canBackspace(Object.assign({}, state, {
                                                       completion: {}
                                                   }), event));
        compare(Session.switchMode(state, "files", true).query, "");
    }

    function test_currencyDecimalConversion() {
        compare(Currency.convert("0.1", "0.2", false), "0.02");
        compare(Currency.convert("9007199254740993", "2", false), "18014398509481986");
        compare(Currency.convert("100", "7.25", false), "725");
        compare(Currency.convert("725", "7.25", true), "100");
        compare(Currency.convert("-1.25", "0.5", true), "-2.5");
        compare(Currency.convert("1", "3", true), "0.333333333333333333333333");
        compare(Currency.convert("2", "3", true), "0.666666666666666666666667");
        compare(Currency.convert("1", "1e-7", false), "0.0000001");
        compare(Currency.convert("0", "7", true), "0");
        compare(Currency.convert("", "1", false), "");
        compare(Currency.convert("1", "0", true), "");
        compare(Currency.convert("1", "-1", false), "");
        compare(Currency.convert("1", "oops", true), "");
        compare(Currency.convert("-", "1", false), "");
    }
    function test_currencyCandidateRanking() {
        const catalog = [
                  {
                      text: "USD",
                      name: "US Dollar"
                  },
                  {
                      text: "AUD",
                      name: "Australian Dollar"
                  },
                  {
                      text: "USN",
                      name: "Next day Dollar"
                  }
              ];
        compare(Currency.candidates(catalog, "usd")[0].text, "USD");
        compare(Currency.candidates(catalog, "us")[0].text, "USD");
        compare(Currency.candidates(catalog, "dollar").length, 3);
        compare(Currency.candidates(catalog, "australian")[0].text, "AUD");
        compare(Currency.candidates(catalog, "missing").length, 0);
        compare(Currency.seed("100 USD to CNY").amount, "100");
        compare(Currency.seed("").to, "EUR");
    }
    function test_timeTemplateInput() {
        compare(Templates.editableTime("2026-09-18T00:30:00+09:00"), "2026-09-18 00:30:00");
        compare(Templates.editableTime("2026-09-17T09:30:00.123456-04:00"), "2026-09-17 09:30:00");
        compare(Templates.editableTime(null), "");
        compare(Templates.timeExpression("0930", "Asia/Shanghai", "Europe/London"),
                "09:30 Asia/Shanghai to Europe/London");
        compare(Templates.timeExpression("9", "", "UTC"), "09:00 to UTC");
        compare(Templates.timeExpression("2026-11-01 01:30", "America/New_York", "UTC"),
                "2026-11-01 01:30 America/New_York to UTC");
        compare(Templates.timeExpression("", "", "UTC"), "");
        compare(Templates.timeExpression("0930", "", ""), "");
    }
}
