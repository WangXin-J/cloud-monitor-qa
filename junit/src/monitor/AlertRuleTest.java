package monitor;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 告警规则单测。重点不是「能跑通」，而是把边界钉死：
 * 等于阈值怎么办、连续几次才算数、冷却期内会不会重复轰炸、恢复后计数清不清零。
 */
class AlertRuleTest {

    @Test
    @DisplayName("连续 N 次满足条件才触发")
    void firesOnlyAfterConsecutiveHits() {
        AlertRule rule = new AlertRule("cpu", ">", 90, 2, 300);

        assertFalse(rule.evaluate(95, 1000), "第 1 次不应该触发");
        assertTrue(rule.evaluate(95, 1001), "第 2 次应该触发");
    }

    @Test
    @DisplayName("等于阈值且算子是 > 时不触发（边界值）")
    void equalToThresholdDoesNotFire() {
        AlertRule rule = new AlertRule("cpu", ">", 90, 1, 300);

        assertFalse(rule.evaluate(90, 1000));
    }

    @Test
    @DisplayName("算子是 >= 时，等于阈值应触发")
    void greaterOrEqualFiresOnEqual() {
        AlertRule rule = new AlertRule("cpu", ">=", 90, 1, 300);

        assertTrue(rule.evaluate(90, 1000));
    }

    @Test
    @DisplayName("冷却期内不重复告警")
    void silenceWindowSuppressesDuplicate() {
        AlertRule rule = new AlertRule("cpu", ">", 90, 1, 300);

        assertTrue(rule.evaluate(95, 1000), "首次触发");
        assertFalse(rule.evaluate(95, 1100), "冷却期内不应重复触发");
        assertTrue(rule.evaluate(95, 1300), "冷却期后再触发");
    }

    @Test
    @DisplayName("指标恢复正常后，连续次数清零")
    void resetCounterOnRecovery() {
        AlertRule rule = new AlertRule("cpu", ">", 90, 2, 0);

        assertFalse(rule.evaluate(95, 1000));
        assertFalse(rule.evaluate(50, 1001), "恢复正常，计数清零");
        assertEquals(0, rule.getHitCount());
        assertFalse(rule.evaluate(95, 1002), "重新开始计数，不应触发");
        assertTrue(rule.evaluate(95, 1003));
    }

    @Test
    @DisplayName("非法构造参数直接抛异常")
    void invalidArgumentsRejected() {
        assertThrows(IllegalArgumentException.class,
                () -> new AlertRule("cpu", ">", 90, 0, 300));
        assertThrows(IllegalArgumentException.class,
                () -> new AlertRule("cpu", ">", 90, 1, -1));
    }

    @Test
    @DisplayName("未知算子应当报错，而不是静默不告警")
    void unknownOperatorThrows() {
        AlertRule rule = new AlertRule("cpu", "==", 90, 1, 300);
        assertThrows(IllegalStateException.class, () -> rule.evaluate(95, 1000));
    }
}
