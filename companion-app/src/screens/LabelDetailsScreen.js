import React, { useState, useEffect } from 'react';
import {
    View, Text, StyleSheet, FlatList, TouchableOpacity,
    ActivityIndicator, Image, Alert, ScrollView
} from 'react-native';
import { getLabelImages, PI_BASE_URL, triggerBoost, getBoostStatus, syncLabelCentroid } from '../services/api';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { Feather } from '@expo/vector-icons';

const COLORS = {
    bg: '#050814',
    cardBg: 'rgba(255, 255, 255, 0.03)',
    cardBorder: 'rgba(255, 255, 255, 0.1)',
    primary: '#00F0FF',
    accent: '#B026FF',
    success: '#00F0FF', 
    text: '#FFFFFF',
    textMuted: '#9CA3AF',
    textDark: '#111827',
};

export default function LabelDetailsScreen({ route, navigation }) {
    const { label, hasAction, action } = route.params;
    const [images, setImages] = useState([]);
    const [loading, setLoading] = useState(true);
    const [augmenting, setAugmenting] = useState(false);
    const [boostProgress, setBoostProgress] = useState(null); // { progress, total, message, status }
    const [error, setError] = useState(null);
    const _pollRef = React.useRef(null);

    useEffect(() => {
        navigation.setOptions({ 
            title: '', // Keep clean header
        });
        loadImages();
    }, [label, navigation]);

    const loadImages = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await getLabelImages(label);
            setImages(res.data.images || []);
        } catch (e) {
            setError('Could not establish link to retrieve visual arrays.');
        } finally {
            setLoading(false);
        }
    };

    const handleBoostAccuracy = async () => {
        setAugmenting(true);
        setBoostProgress({ progress: 0, total: 0, message: 'Starting boost pipeline...', status: 'pending' });
        try {
            const res = await triggerBoost(label, 150);
            const jobId = res.data.job_id;

            // Poll /boost/status every 2 seconds
            _pollRef.current = setInterval(async () => {
                try {
                    const statusRes = await getBoostStatus(jobId);
                    const job = statusRes.data;
                    setBoostProgress(job);

                    if (job.status === 'done' || job.status === 'failed') {
                        clearInterval(_pollRef.current);
                        setAugmenting(false);
                        if (job.status === 'done') {
                            // Sync to confirm
                            await syncLabelCentroid(label);
                            Alert.alert(
                                '⚡ Boost Complete',
                                job.message,
                                [{ text: 'Acknowledged' }]
                            );
                        } else {
                            Alert.alert('Transmission Error', job.message);
                        }
                        setBoostProgress(null);
                    }
                } catch (pollErr) {
                    // Ignore transient polling errors
                }
            }, 2000);
        } catch (e) {
            setAugmenting(false);
            setBoostProgress(null);
            Alert.alert('Transmission Error', 'Failed to start boost sequence. Verify uplink.');
        }
    };

    const renderItem = ({ item }) => (
        <View style={styles.imageContainer}>
            <Image
                source={{ uri: `${PI_BASE_URL}/learn/image/${encodeURIComponent(item)}?t=${Date.now()}` }}
                style={styles.image}
            />
            <LinearGradient
                colors={['transparent', 'rgba(5, 8, 20, 0.8)']}
                style={styles.imageOverlay}
            />
        </View>
    );

    return (
        <View style={styles.container}>
            {/* Background glowing orbs */}
            <View style={styles.glowTopLeft} />
            <View style={styles.glowBottomRight} />

            <ScrollView contentContainerStyle={styles.scrollContent}>
                <BlurView intensity={30} tint="dark" style={styles.headerCard}>
                    <Text style={styles.headerLabel}>{label}</Text>
                    {hasAction ? (
                        <LinearGradient 
                            colors={['rgba(0, 240, 255, 0.15)', 'rgba(0, 240, 255, 0.05)']} 
                            style={styles.actionBadge}
                            start={{x: 0, y: 0}} end={{x: 1, y: 1}}
                        >
                            <Feather name="zap" size={14} color={COLORS.primary} style={styles.actionIcon} />
                            <Text style={styles.actionText}>{action}</Text>
                        </LinearGradient>
                    ) : (
                        <Text style={styles.noAction}>Unassigned memory block</Text>
                    )}
                </BlurView>

                <View style={styles.sectionHeader}>
                    <View style={styles.sectionTitleRow}>
                        <Feather name="grid" size={18} color={COLORS.textMuted} />
                        <Text style={styles.sectionTitle}>Visual Arrays</Text>
                    </View>
                    
                    {images.length > 0 && (
                        <TouchableOpacity
                            activeOpacity={0.8}
                            onPress={handleBoostAccuracy}
                            disabled={augmenting}
                        >
                            <LinearGradient 
                                colors={augmenting ? [COLORS.cardBg, COLORS.cardBg] : [COLORS.primary, '#00A3FF']}
                                style={[styles.accuracyBtn, augmenting && styles.accuracyBtnDisabled]}
                                start={{x: 0, y: 0}} end={{x: 1, y: 1}}
                            >
                                {augmenting ? (
                                    <View style={styles.progressContainer}>
                                        <ActivityIndicator size="small" color={COLORS.primary} />
                                        {boostProgress && boostProgress.total > 0 ? (
                                            <Text style={styles.progressText}>
                                                {Math.round((boostProgress.progress / boostProgress.total) * 100)}%
                                            </Text>
                                        ) : null}
                                    </View>
                                ) : (
                                    <>
                                        <Feather name="cpu" size={16} color={COLORS.textDark} style={{ marginRight: 6 }} />
                                        <Text style={styles.accuracyBtnText}>Deep Learn</Text>
                                    </>
                                )}
                            </LinearGradient>
                        </TouchableOpacity>
                    )}
                </View>

                {loading ? (
                    <View style={styles.center}>
                        <ActivityIndicator size="large" color={COLORS.primary} />
                    </View>
                ) : error ? (
                    <View style={styles.center}>
                        <Feather name="alert-circle" size={48} color="#EF4444" style={{ marginBottom: 16, opacity: 0.8 }} />
                        <Text style={styles.errorText}>{error}</Text>
                        <TouchableOpacity onPress={loadImages} style={styles.retryBtn}>
                            <Text style={styles.retryText}>Retry Uplink</Text>
                        </TouchableOpacity>
                    </View>
                ) : images.length === 0 ? (
                    <View style={styles.center}>
                        <Feather name="image" size={48} color={COLORS.textMuted} style={{ marginBottom: 16, opacity: 0.5 }} />
                        <Text style={styles.muted}>No visual data found in memory banks.</Text>
                    </View>
                ) : (
                    <FlatList
                        data={images}
                        keyExtractor={item => item}
                        renderItem={renderItem}
                        numColumns={2}
                        scrollEnabled={false} // Since we're inside a scrollview
                        contentContainerStyle={styles.list}
                        columnWrapperStyle={styles.columnWrapper}
                    />
                )}
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: COLORS.bg },
    scrollContent: { paddingTop: 100, paddingBottom: 120 },
    glowTopLeft: { position: 'absolute', top: -100, left: -50, width: 300, height: 300, borderRadius: 150, backgroundColor: 'rgba(0, 240, 255, 0.1)', opacity: 0.8, blurRadius: 60 },
    glowBottomRight: { position: 'absolute', bottom: 100, right: -100, width: 300, height: 300, borderRadius: 150, backgroundColor: 'rgba(176, 38, 255, 0.1)', opacity: 0.8, blurRadius: 60 },
    center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, minHeight: 200 },
    headerCard: {
        backgroundColor: COLORS.cardBg,
        padding: 24,
        margin: 16,
        borderRadius: 20,
        borderWidth: 1,
        borderColor: COLORS.cardBorder,
        alignItems: 'center',
        overflow: 'hidden'
    },
    headerLabel: {
        fontFamily: 'Outfit_800ExtraBold',
        fontSize: 32,
        color: COLORS.text,
        textTransform: 'capitalize',
        marginBottom: 12,
        letterSpacing: 0.5,
        textAlign: 'center'
    },
    actionBadge: {
        flexDirection: 'row',
        alignItems: 'center',
        borderRadius: 12,
        paddingHorizontal: 16,
        paddingVertical: 8,
        gap: 8,
        borderWidth: 1,
        borderColor: 'rgba(0, 240, 255, 0.3)'
    },
    actionIcon: { },
    actionText: { fontFamily: 'Outfit_600SemiBold', fontSize: 13, color: COLORS.primary, letterSpacing: 0.5 },
    noAction: { fontFamily: 'Outfit_400Regular', fontSize: 14, color: COLORS.textMuted, fontStyle: 'italic' },
    sectionHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 16,
        marginBottom: 16,
        marginTop: 8
    },
    sectionTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    sectionTitle: {
        fontFamily: 'Outfit_800ExtraBold',
        fontSize: 20,
        color: COLORS.text,
        letterSpacing: 0.5
    },
    accuracyBtn: {
        paddingHorizontal: 16,
        paddingVertical: 10,
        borderRadius: 12,
        flexDirection: 'row',
        alignItems: 'center',
        shadowColor: COLORS.primary,
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8
    },
    accuracyBtnDisabled: {
        borderWidth: 1,
        borderColor: COLORS.cardBorder,
        shadowOpacity: 0,
    },
    accuracyBtnText: {
        fontFamily: 'Outfit_800ExtraBold',
        color: COLORS.textDark,
        fontSize: 13,
        letterSpacing: 0.5
    },
    list: { paddingHorizontal: 12 },
    columnWrapper: { justifyContent: 'space-between', marginBottom: 12 },
    imageContainer: {
        width: '48%',
        aspectRatio: 1,
        borderRadius: 16,
        overflow: 'hidden',
        borderWidth: 1,
        borderColor: COLORS.cardBorder,
        backgroundColor: COLORS.cardBg
    },
    image: {
        width: '100%',
        height: '100%',
        resizeMode: 'cover'
    },
    imageOverlay: {
        position: 'absolute',
        bottom: 0, left: 0, right: 0,
        height: '40%'
    },
    muted: { fontFamily: 'Outfit_400Regular', color: COLORS.textMuted, textAlign: 'center', fontSize: 15, lineHeight: 22 },
    errorText: { fontFamily: 'Outfit_600SemiBold', color: '#EF4444', textAlign: 'center', marginBottom: 20, fontSize: 15, lineHeight: 22 },
    retryBtn: { backgroundColor: 'transparent', borderWidth: 1, borderColor: COLORS.cardBorder, paddingHorizontal: 24, paddingVertical: 12, borderRadius: 12 },
    retryText: { fontFamily: 'Outfit_600SemiBold', color: COLORS.text, fontSize: 14 },
    progressContainer: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    progressText: { fontFamily: 'Outfit_600SemiBold', color: COLORS.primary, fontSize: 13 },
    progressCard: {
        marginHorizontal: 16, marginBottom: 12,
        padding: 16,
        borderRadius: 16,
        borderWidth: 1,
        borderColor: 'rgba(0, 240, 255, 0.2)',
        backgroundColor: 'rgba(0, 240, 255, 0.04)',
    },
    progressMsg: {
        fontFamily: 'Outfit_400Regular', color: COLORS.textMuted, fontSize: 13, marginBottom: 10, lineHeight: 18,
    },
    progressTrack: {
        height: 6, borderRadius: 3, backgroundColor: 'rgba(255,255,255,0.08)', overflow: 'hidden',
    },
    progressFill: {
        height: '100%', borderRadius: 3, backgroundColor: COLORS.primary,
    },
    progressPercent: {
        fontFamily: 'Outfit_600SemiBold', color: COLORS.primary, fontSize: 12, marginTop: 6, textAlign: 'right',
    },
});
